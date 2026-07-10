"""FreshAlert 스케줄러.

배치 작업(데이터 수집, 분석, 알림 발송)을 스케줄링하는 모듈.
실제 운영 환경에서는 Celery + Redis Beat를 사용하지만,
MVP에서는 단순 asyncio 기반 스케줄러를 제공한다.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.services.fresh_alert.analyzer import (
    calculate_moving_average,
    calculate_price_drop_rate,
    calculate_qty_increase_rate,
    calculate_recommend_score,
    check_keyword_trigger,
    detect_price_anomaly,
    is_in_season,
    select_top_recommendations,
)
from app.services.fresh_alert.alert_service import (
    create_notification,
    generate_category_notification,
    generate_keyword_notification,
    generate_recommend_notification,
)
from app.services.fresh_alert.repository import fresh_alert_repo

logger = logging.getLogger(__name__)


async def run_daily_analysis() -> dict:
    """일별 분석을 실행한다.

    매일 06:30 실행 예정.
    - 모든 품목에 대해 30일 이동평균, 하락률, 물량 증가율 계산
    - 추천 점수 산출
    - 이상치 탐지

    Returns:
        분석 결과 요약 dict
    """
    from app.domain.fresh_alert_models import DailyAnalysis

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y%m%d")
    month = now.month

    items = fresh_alert_repo.list_items()
    analysis_count = 0
    anomaly_count = 0

    for item in items:
        history = fresh_alert_repo.get_price_history(item.item_id, days=90)
        if not history:
            continue

        prices = [r.avg_price for r in history]
        qtys = [r.total_qty for r in history]

        avg_30d = calculate_moving_average(prices, 30)
        avg_7d_qty = calculate_moving_average(qtys, 7)
        current_price = prices[-1]
        current_qty = qtys[-1] if qtys else 0

        price_drop = calculate_price_drop_rate(current_price, avg_30d)
        qty_increase = calculate_qty_increase_rate(current_qty, avg_7d_qty)
        season = is_in_season(month, item.season_start, item.season_end)
        score = calculate_recommend_score(price_drop, qty_increase, season)
        anomaly = detect_price_anomaly(current_price, prices)

        analysis = DailyAnalysis(
            item_id=item.item_id,
            analysis_date=today_str,
            avg_30d=int(avg_30d),
            current_price=current_price,
            price_drop_rate=price_drop,
            qty_increase_rate=qty_increase,
            is_season=season,
            recommend_score=score,
        )
        fresh_alert_repo.save_daily_analysis(item.item_id, analysis)
        analysis_count += 1

        if anomaly != "NORMAL":
            anomaly_count += 1
            logger.info(
                "Price anomaly detected: item=%s, status=%s, price=%d",
                item.item_id, anomaly, current_price,
            )

    logger.info(
        "Daily analysis completed: items=%d, anomalies=%d",
        analysis_count, anomaly_count,
    )
    return {"analyzed": analysis_count, "anomalies": anomaly_count}


async def run_recommendation_generation() -> dict:
    """오늘의 추천을 생성한다.

    매일 07:00 실행 예정.
    - 분석 결과 기반 TOP 5 선정
    - 전체 사용자에게 추천 알림 발송

    Returns:
        추천 결과 요약
    """
    from app.domain.fresh_alert_models import DailyRecommendation, RecommendationItem

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y%m%d")

    analyses = fresh_alert_repo.get_daily_analyses(today_str)
    if not analyses:
        # 분석이 안 되어 있으면 먼저 실행
        await run_daily_analysis()
        analyses = fresh_alert_repo.get_daily_analyses(today_str)

    analysis_dicts = [
        {
            "item_id": a.item_id,
            "item_name": _get_item_name(a.item_id),
            "large_name": _get_item_large_name(a.item_id),
            "current_price": a.current_price,
            "avg_30d": a.avg_30d,
            "price_drop_rate": a.price_drop_rate,
            "qty_increase_rate": a.qty_increase_rate,
            "is_season": a.is_season,
            "recommend_score": a.recommend_score,
        }
        for a in analyses
    ]

    top = select_top_recommendations(analysis_dicts, top_n=5)

    rec_items = [
        RecommendationItem(
            rank=i + 1,
            item_id=item["item_id"],
            item_name=item["item_name"],
            large_name=item["large_name"],
            current_price=item["current_price"],
            avg_30d=item["avg_30d"],
            price_drop_rate=item["price_drop_rate"],
            is_season=item["is_season"],
            recommend_score=item["recommend_score"],
        )
        for i, item in enumerate(top)
    ]

    recommendation = DailyRecommendation(date=today_str, items=rec_items)
    fresh_alert_repo.save_recommendation(recommendation)

    # 추천 알림 생성
    notif_msg = generate_recommend_notification(
        [{"item_name": r.item_name, "price_drop_rate": r.price_drop_rate, "is_season": r.is_season} for r in rec_items],
        today_str,
    )
    notif = create_notification(
        user_id="user_dev_01",
        notif_type="recommend",
        title=notif_msg["title"],
        body=notif_msg["body"],
    )
    fresh_alert_repo.add_notification(
        __import__("app.domain.fresh_alert_models", fromlist=["Notification"]).Notification(**notif)
    )

    logger.info("Recommendation generated: %d items", len(rec_items))
    return {"recommended_count": len(rec_items), "date": today_str}


async def run_keyword_alerts() -> dict:
    """키워드 알림을 확인하고 발송한다.

    매일 07:00 및 12:00, 18:00 실행 예정.

    Returns:
        발송 결과 요약
    """
    # 현재 dev 사용자의 구독만 처리
    user_id = "user_dev_01"
    subs = fresh_alert_repo.get_keyword_subscriptions(user_id)
    triggered_count = 0

    for sub in subs:
        if not sub.enabled:
            continue

        history = fresh_alert_repo.get_price_history(sub.item_id, days=30)
        if not history:
            continue

        prices = [r.avg_price for r in history]
        avg_30d = calculate_moving_average(prices, 30)
        current_price = prices[-1]

        if check_keyword_trigger(current_price, avg_30d, sub.threshold_type, sub.threshold_value):
            price_drop = calculate_price_drop_rate(current_price, avg_30d)
            notif_msg = generate_keyword_notification(
                sub.item_name, current_price, avg_30d, price_drop,
            )
            notif = create_notification(
                user_id=user_id,
                notif_type="keyword",
                title=notif_msg["title"],
                body=notif_msg["body"],
                item_id=sub.item_id,
            )
            from app.domain.fresh_alert_models import Notification as NotifModel
            fresh_alert_repo.add_notification(NotifModel(**notif))
            triggered_count += 1

    logger.info("Keyword alerts checked: triggered=%d", triggered_count)
    return {"checked": len(subs), "triggered": triggered_count}


def _get_item_name(item_id: str) -> str:
    """품목 ID로 이름을 조회한다."""
    item = fresh_alert_repo.get_item(item_id)
    return item.mid_name if item else item_id


def _get_item_large_name(item_id: str) -> str:
    """품목 ID로 대분류명을 조회한다."""
    item = fresh_alert_repo.get_item(item_id)
    return item.large_name if item else ""
