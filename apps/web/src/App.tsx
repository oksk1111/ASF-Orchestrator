import { useEffect, useMemo, useState } from "react";

import { BasketEnvelope, ForecastEnvelope, RouteEnvelope, fetchBasket, fetchForecasts, fetchRoute, issueToken } from "./api/client";

function formatWon(value: number): string {
  return new Intl.NumberFormat("ko-KR").format(Math.round(value));
}

export default function App() {
  const [basket, setBasket] = useState<BasketEnvelope | null>(null);
  const [forecast, setForecast] = useState<ForecastEnvelope | null>(null);
  const [route, setRoute] = useState<RouteEnvelope | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        setLoading(true);
        const token = await issueToken("user_dev_01");
        const [basketData, forecastData, routeData] = await Promise.all([
          fetchBasket(token),
          fetchForecasts(),
          fetchRoute(),
        ]);
        setBasket(basketData);
        setForecast(forecastData);
        setRoute(routeData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "unknown error");
      } finally {
        setLoading(false);
      }
    };

    void bootstrap();
  }, []);

  const heroStats = useMemo(() => {
    if (!basket) {
      return {
        items: 0,
        discountRate: 0,
        points: 0,
      };
    }
    return {
      items: basket.data.summary.total_items_count,
      discountRate: Math.round(basket.data.summary.total_discount_rate * 100),
      points: basket.data.summary.estimated_esg_points,
    };
  }, [basket]);

  return (
    <div className="page">
      <div className="bg-shape bg-shape-one" />
      <div className="bg-shape bg-shape-two" />

      <header className="announcement-bar">
        <span>농가 폐기 0원 수렴을 위한 실시간 수급 오케스트레이션 테스트베드 운영 중</span>
        <nav>
          <a href="#dashboard">B2B 대시보드</a>
          <a href="#mobile">모바일 UX</a>
        </nav>
      </header>

      <div className="top-nav">
        <div className="brand-mark">A</div>
        <strong>ASF-Orchestrator</strong>
        <ul>
          <li>Products</li>
          <li>Forecast</li>
          <li>Logistics</li>
          <li>ESG</li>
        </ul>
      </div>

      <main className="container">
        <section className="hero">
          <article>
            <h1>
              수급 예측과 건강 추천을
              <span> 하나의 장바구니</span>
              로 연결합니다
            </h1>
            <p>
              ASF-Orchestrator는 실시간 공급과잉 지표, 사용자 건강 목표, 물류 탄소비용을 동시에 계산해
              동적 가격과 친환경 배송 경로를 함께 제안합니다.
            </p>
            <div className="cta-row">
              <button className="btn-primary">플랫폼 시뮬레이션 시작</button>
              <button className="btn-secondary">아키텍처 보기</button>
            </div>

            <div className="stats-row">
              <div className="stats-card stats-highlight">
                <b>{heroStats.discountRate}%</b>
                <span>예상 할인율</span>
              </div>
              <div className="stats-card">
                <b>{heroStats.items}</b>
                <span>추천 품목 수</span>
              </div>
              <div className="stats-card">
                <b>{heroStats.points}</b>
                <span>예상 ESG 포인트</span>
              </div>
            </div>
          </article>

          <aside>
            <div className="hero-visual">
              <div className="lime-panel" />
              <div className="floating-chip">Smart Basket Ready</div>
              <div className="floating-card">
                다음 배치에서 양배추·양파 수급 과잉 위험이 높습니다. 추천 가중치 β가 자동 상향됩니다.
              </div>
            </div>
          </aside>
        </section>

        <section className="module-grid" id="dashboard">
          <article className="module-card">
            <h2>AI Basket (B2C)</h2>
            {loading && <p>데이터 로딩 중...</p>}
            {error && <p className="error">{error}</p>}
            {!loading && basket && (
              <>
                <p className="module-summary">
                  예상 원가 {formatWon(basket.data.summary.estimated_original_price)}원 →
                  할인 후 {formatWon(basket.data.summary.estimated_discounted_price)}원
                </p>
                <ul className="item-list">
                  {basket.data.items.map((item) => (
                    <li key={item.product_code}>
                      <div>
                        <strong>{item.product_name}</strong>
                        <small>{item.nutrition_match_reason}</small>
                      </div>
                      <div className="price-col">
                        <span>{formatWon(item.discounted_price)}원</span>
                        <em>{item.oversupply_risk_level}</em>
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </article>

          <article className="module-card">
            <h2>VRP Logistics (B2B)</h2>
            {!loading && route && (
              <>
                <p className="module-summary">
                  CO2 절감률 {route.data.base_co2_reduction_percentage}%
                </p>
                <ul className="item-list">
                  {route.data.optimized_routes.map((item) => (
                    <li key={item.route_index}>
                      <div>
                        <strong>Route {item.route_index}</strong>
                        <small>{item.path_destination_ids.join(" → ")}</small>
                      </div>
                      <div className="price-col">
                        <span>{Math.round(item.total_distance_meters / 1000)}km</span>
                        <em>{item.co2_emitted_kg}kg CO2</em>
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </article>

          <article className="module-card wide">
            <h2>14일 수급/가격 예측</h2>
            {!loading && forecast && (
              <div className="forecast-grid">
                {forecast.data.map((item) => (
                  <div key={item.product_code} className="forecast-item">
                    <strong>{item.product_code}</strong>
                    <span>P50 {formatWon(item.p50_predicted_price)}원</span>
                    <span>Risk {(item.oversupply_risk_index * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
          </article>
        </section>

        <section className="feature-section" id="mobile">
          <h2>모듈 시스템 맵</h2>
          <div className="feature-grid">
            <div>
              <h3>Data Ingestion</h3>
              <p>Airflow 배치 시나리오를 기준으로 공공 데이터를 Feature Store에 동기화</p>
            </div>
            <div>
              <h3>AI Orchestration</h3>
              <p>TFT 예측과 다목적 추천함수를 결합해 사용자별 장바구니 생성</p>
            </div>
            <div>
              <h3>Execution Layer</h3>
              <p>동적 할인율, ESG 포인트, VRP 배차 결과를 API로 실시간 전달</p>
            </div>
          </div>
        </section>

        <section className="community-card">
          <div>
            <h2>내일 아침의 장보기가 산지 폐기를 멈춥니다.</h2>
            <p>ASF-Orchestrator는 소비자와 생산자 데이터를 같은 목적함수로 연결합니다.</p>
          </div>
          <button className="btn-primary">파트너십 문의</button>
        </section>
      </main>
    </div>
  );
}
