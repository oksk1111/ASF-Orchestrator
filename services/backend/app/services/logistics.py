from __future__ import annotations

import math

from app.domain.models import (
    CalculateRouteRequest,
    CalculateRouteResponse,
    Coordinate,
    DeliveryDestination,
    OptimizedRoute,
    RouteEnvelope,
)


def _haversine_meters(a: Coordinate, b: Coordinate) -> float:
    earth_radius_m = 6371000.0
    d_lat = math.radians(b.latitude - a.latitude)
    d_lon = math.radians(b.longitude - a.longitude)
    lat1 = math.radians(a.latitude)
    lat2 = math.radians(b.latitude)

    h = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    )
    return 2 * earth_radius_m * math.atan2(math.sqrt(h), math.sqrt(1 - h))


class LogisticsService:
    def calculate_route(self, request: CalculateRouteRequest) -> RouteEnvelope:
        pending = list(request.destinations)
        routes: list[OptimizedRoute] = []
        route_index = 1
        optimized_distance = 0.0

        while pending:
            capacity_left = request.vehicle_max_capacity_kg
            current = request.warehouse_coordinate
            path: list[str] = []
            total_distance = 0.0

            while pending:
                candidates = [d for d in pending if d.demand_weight_kg <= capacity_left]
                if not candidates:
                    break

                next_node = min(
                    candidates,
                    key=lambda d: _haversine_meters(current, d.coordinate),
                )
                hop = _haversine_meters(current, next_node.coordinate)
                total_distance += hop
                path.append(next_node.destination_id)
                current = next_node.coordinate
                capacity_left -= next_node.demand_weight_kg
                pending.remove(next_node)

            if not path:
                # Heavy destination fallback
                heaviest = pending.pop(0)
                total_distance = _haversine_meters(
                    request.warehouse_coordinate, heaviest.coordinate
                )
                total_distance += _haversine_meters(
                    heaviest.coordinate, request.warehouse_coordinate
                )
                path = [heaviest.destination_id]
            else:
                total_distance += _haversine_meters(current, request.warehouse_coordinate)

            optimized_distance += total_distance
            travel_time = (total_distance / 1000.0) / 35.0 * 3600.0
            co2_emitted = (total_distance / 1000.0) * 0.21

            routes.append(
                OptimizedRoute(
                    route_index=route_index,
                    path_destination_ids=path,
                    total_distance_meters=round(total_distance, 2),
                    total_travel_time_seconds=round(travel_time, 2),
                    co2_emitted_kg=round(co2_emitted, 3),
                )
            )
            route_index += 1

        naive_distance = 0.0
        for destination in request.destinations:
            leg = _haversine_meters(request.warehouse_coordinate, destination.coordinate)
            naive_distance += leg * 2

        reduction = 0.0
        if naive_distance > 0:
            reduction = max(0.0, ((naive_distance - optimized_distance) / naive_distance) * 100.0)

        payload = CalculateRouteResponse(
            warehouse_id=request.warehouse_id,
            optimized_routes=routes,
            base_co2_reduction_percentage=round(reduction, 2),
        )
        return RouteEnvelope(data=payload)
