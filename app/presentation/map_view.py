import plotly.graph_objects as go


BUILDING_X_RANGE = (0, 36)
BUILDING_Y_RANGE = (0, 24)
BUILDING_Z_RANGE = (0, 18)
FLOOR_Z_LEVELS = (3.2, 6.4, 9.6, 12.8)
ROOM_HALF_WIDTH = 2.2
ROOM_HALF_DEPTH = 2.2
ROOM_HEIGHT = 2.8
CORE_X_RANGE = (16.8, 19.2)
CORE_Y_RANGE = (9.5, 12.0)
ATRIUM_X_RANGE = (25.0, 35.0)
ATRIUM_Y_RANGE = (1.0, 9.5)


def _coordinate_values(targets):
    x_values = []
    y_values = []
    z_values = []

    for target in targets:
        coords = target["estimated_coordinates"]
        if isinstance(coords, dict):
            x_values.append(coords["x"])
            y_values.append(coords["y"])
            z_values.append(coords["z"])
        else:
            x_values.append(coords[0])
            y_values.append(coords[1])
            z_values.append(coords[2])

    return x_values, y_values, z_values


def _building_footprint(bim_data=None):
    footprint = (bim_data or {}).get("building_model", {}).get("footprint", {})
    return (
        footprint.get("x_min", BUILDING_X_RANGE[0]),
        footprint.get("x_max", BUILDING_X_RANGE[1]),
        footprint.get("y_min", BUILDING_Y_RANGE[0]),
        footprint.get("y_max", BUILDING_Y_RANGE[1]),
        footprint.get("z_min", BUILDING_Z_RANGE[0]),
        footprint.get("z_max", BUILDING_Z_RANGE[1]),
    )


def _floor_levels(bim_data=None):
    levels = (bim_data or {}).get("building_model", {}).get("floor_levels_z")
    return tuple(levels) if levels else FLOOR_Z_LEVELS


def add_building_wireframe(fig, bim_data=None):
    x0, x1, y0, y1, z0, z1 = _building_footprint(bim_data)

    corners = {
        "000": (x0, y0, z0),
        "100": (x1, y0, z0),
        "110": (x1, y1, z0),
        "010": (x0, y1, z0),
        "001": (x0, y0, z1),
        "101": (x1, y0, z1),
        "111": (x1, y1, z1),
        "011": (x0, y1, z1),
    }

    edges = [
        ("000", "100"), ("100", "110"), ("110", "010"), ("010", "000"),
        ("001", "101"), ("101", "111"), ("111", "011"), ("011", "001"),
        ("000", "001"), ("100", "101"), ("110", "111"), ("010", "011"),
    ]

    for start, end in edges:
        fig.add_trace(
            go.Scatter3d(
                x=[corners[start][0], corners[end][0]],
                y=[corners[start][1], corners[end][1]],
                z=[corners[start][2], corners[end][2]],
                mode="lines",
                line={"color": "rgba(120, 140, 160, 0.35)", "width": 3},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    for x in (CORE_X_RANGE[0], CORE_X_RANGE[1]):
        for y in (CORE_Y_RANGE[0], CORE_Y_RANGE[1]):
            fig.add_trace(
                go.Scatter3d(
                    x=[x, x],
                    y=[y, y],
                    z=[z0, z1],
                    mode="lines",
                    line={"color": "rgba(71, 85, 105, 0.42)", "width": 2},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    facade_lines = [
        ((x0, y0, z0), (x0, y0, z1)),
        ((x1, y0, z0), (x1, y0, z1)),
        ((x0, y1, z0), (x0, y1, z1)),
        ((x1, y1, z0), (x1, y1, z1)),
        ((ATRIUM_X_RANGE[0], ATRIUM_Y_RANGE[0], z0), (ATRIUM_X_RANGE[0], ATRIUM_Y_RANGE[0], z1)),
        ((ATRIUM_X_RANGE[1], ATRIUM_Y_RANGE[0], z0), (ATRIUM_X_RANGE[1], ATRIUM_Y_RANGE[0], z1)),
    ]
    for start, end in facade_lines:
        fig.add_trace(
            go.Scatter3d(
                x=[start[0], end[0]],
                y=[start[1], end[1]],
                z=[start[2], end[2]],
                mode="lines",
                line={"color": "rgba(8, 145, 178, 0.34)", "width": 2},
                hoverinfo="skip",
                showlegend=False,
            )
        )


def add_floor_planes(fig, bim_data=None):
    x0, x1, y0, y1, _, _ = _building_footprint(bim_data)

    for z in _floor_levels(bim_data):
        fig.add_trace(
            go.Surface(
                x=[[x0, x1], [x0, x1]],
                y=[[y0, y0], [y1, y1]],
                z=[[z, z], [z, z]],
                opacity=0.08,
                colorscale=[[0, "rgb(170, 185, 200)"], [1, "rgb(170, 185, 200)"]],
                showscale=False,
                hoverinfo="skip",
            )
        )
        for x in range(int(x0), int(x1) + 1, 5):
            fig.add_trace(
                go.Scatter3d(
                    x=[x, x],
                    y=[y0, y1],
                    z=[z, z],
                    mode="lines",
                    line={"color": "rgba(71, 85, 105, 0.18)", "width": 1},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        fig.add_trace(
            go.Scatter3d(
                x=[CORE_X_RANGE[0], CORE_X_RANGE[1], CORE_X_RANGE[1], CORE_X_RANGE[0], CORE_X_RANGE[0]],
                y=[CORE_Y_RANGE[0], CORE_Y_RANGE[0], CORE_Y_RANGE[1], CORE_Y_RANGE[1], CORE_Y_RANGE[0]],
                z=[z, z, z, z, z],
                mode="lines",
                line={"color": "rgba(15, 23, 42, 0.36)", "width": 4},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter3d(
                x=[ATRIUM_X_RANGE[0], ATRIUM_X_RANGE[1], ATRIUM_X_RANGE[1], ATRIUM_X_RANGE[0], ATRIUM_X_RANGE[0]],
                y=[ATRIUM_Y_RANGE[0], ATRIUM_Y_RANGE[0], ATRIUM_Y_RANGE[1], ATRIUM_Y_RANGE[1], ATRIUM_Y_RANGE[0]],
                z=[z, z, z, z, z],
                mode="lines",
                line={"color": "rgba(8, 145, 178, 0.35)", "width": 3},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        for y in range(int(y0), int(y1) + 1, 5):
            fig.add_trace(
                go.Scatter3d(
                    x=[x0, x1],
                    y=[y, y],
                    z=[z, z],
                    mode="lines",
                    line={"color": "rgba(71, 85, 105, 0.18)", "width": 1},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )


def _point_from_xyz(point):
    return (point["x"], point["y"], point["z"])


def _room_dimensions(room):
    if "dimensions" in room:
        return room["dimensions"]

    name = room["room_name"].lower()
    if "living" in name or "main" in name:
        return {"width": 5.8, "depth": 5.2, "height": 2.8}
    if "kitchen" in name:
        return {"width": 5.0, "depth": 4.5, "height": 2.8}
    if "bedroom" in name:
        return {"width": 5.0, "depth": 4.6, "height": 2.8}
    return {"width": 5.0, "depth": 4.6, "height": 2.8}


def _box_vertices(center, half_width=ROOM_HALF_WIDTH, half_depth=ROOM_HALF_DEPTH, height=ROOM_HEIGHT):
    x, y, z = center
    z0 = max(0.0, z - height / 2)
    z1 = z0 + height
    x0, x1 = x - half_width, x + half_width
    y0, y1 = y - half_depth, y + half_depth
    return [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]


def _room_bounds(room):
    bounds = room.get("post_collapse_bounds") or room.get("bounds")
    if bounds:
        return bounds

    center = _point_from_xyz(room.get("post_collapse_coordinates", room["original_coordinates"]))
    dims = _room_dimensions(room)
    x, y, z = center
    return {
        "x_min": x - dims["width"] / 2,
        "x_max": x + dims["width"] / 2,
        "y_min": y - dims["depth"] / 2,
        "y_max": y + dims["depth"] / 2,
        "z_min": max(0.0, z - dims["height"] / 2),
        "z_max": max(0.0, z - dims["height"] / 2) + dims["height"],
    }


def _box_vertices_from_bounds(bounds):
    x0, x1 = bounds["x_min"], bounds["x_max"]
    y0, y1 = bounds["y_min"], bounds["y_max"]
    z0, z1 = bounds["z_min"], bounds["z_max"]
    return [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]


def _box_edges(vertices):
    edge_indices = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    x_values = []
    y_values = []
    z_values = []
    for start, end in edge_indices:
        x_values.extend([vertices[start][0], vertices[end][0], None])
        y_values.extend([vertices[start][1], vertices[end][1], None])
        z_values.extend([vertices[start][2], vertices[end][2], None])
    return x_values, y_values, z_values


def add_room_volumes(fig, bim_data):
    if not bim_data:
        return

    for room in bim_data.get("rooms", []):
        vertices = _box_vertices_from_bounds(_room_bounds(room))
        x, y, z = zip(*vertices)
        damage = room.get("structural_damage_pct", 0)
        color = "rgba(220, 38, 38, 0.20)" if damage >= 70 else "rgba(245, 158, 11, 0.16)" if damage >= 45 else "rgba(14, 165, 233, 0.12)"
        floor = room.get("floor", "?")
        grid_cell = room.get("grid_cell", {})

        fig.add_trace(
            go.Mesh3d(
                x=x,
                y=y,
                z=z,
                i=[0, 0, 0, 1, 2, 4, 5, 6, 4, 5, 1, 2],
                j=[1, 2, 4, 5, 3, 5, 6, 7, 7, 6, 5, 6],
                k=[2, 3, 5, 6, 7, 7, 7, 4, 0, 1, 2, 3],
                color=color,
                opacity=0.42,
                flatshading=True,
                hovertext=(
                    f"<b>{room['room_name']}</b><br>"
                    f"Room ID: {room['room_id']}<br>"
                    f"Floor: {floor}<br>"
                    f"Grid: C{grid_cell.get('column', '?')} / R{grid_cell.get('row', '?')}<br>"
                    f"Damage: {damage}%"
                ),
                hoverinfo="text",
                name=room["room_id"],
                showlegend=False,
            )
        )
        edge_x, edge_y, edge_z = _box_edges(vertices)
        fig.add_trace(
            go.Scatter3d(
                x=edge_x,
                y=edge_y,
                z=edge_z,
                mode="lines",
                line={"color": "rgba(15, 23, 42, 0.38)", "width": 2},
                hoverinfo="skip",
                showlegend=False,
            )
        )


def add_live_ble_devices(fig, live_devices):
    if not live_devices:
        return

    x_values = [device["estimated_coordinates"][0] for device in live_devices]
    y_values = [device["estimated_coordinates"][1] for device in live_devices]
    z_values = [device["estimated_coordinates"][2] for device in live_devices]
    hover_text = [
        (
            f"<b>LIVE BLE DEVICE</b><br>"
            f"Name: {device.get('name') or 'Unknown'}<br>"
            f"Address: {device.get('address', 'Unknown')}<br>"
            f"RSSI: {device.get('rssi', 'n/a')} dBm<br>"
            f"Estimated: X={coords[0]:.2f}, Y={coords[1]:.2f}, Z={coords[2]:.2f}<br>"
            f"Source: Real-time Bluetooth scan"
        )
        for device, coords in zip(live_devices, [d["estimated_coordinates"] for d in live_devices])
    ]

    fig.add_trace(
        go.Scatter3d(
            x=x_values,
            y=y_values,
            z=z_values,
            mode="markers+text",
            text=[f"LIVE<br>{device.get('name') or device.get('short_id', 'BLE')}" for device in live_devices],
            textposition="top center",
            hovertext=hover_text,
            hoverinfo="text",
            marker={
                "size": 14,
                "color": "#ef0000",
                "symbol": "circle",
                "opacity": 1.0,
                "line": {"color": "#ffffff", "width": 3},
            },
            name="LIVE BLE critical overlay",
        )
    )


def build_static_figure(targets, bim_data=None):
    fig = go.Figure()
    add_floor_planes(fig, bim_data)
    add_room_volumes(fig, bim_data)
    add_building_wireframe(fig, bim_data)

    x_values, y_values, z_values = _coordinate_values(targets)
    urgency_scores = [target["medical_urgency_score"] for target in targets]
    marker_sizes = [10 + score * 0.28 for score in urgency_scores]

    hover_text = []
    for target, x, y, z in zip(targets, x_values, y_values, z_values):
        hover_text.append(
            f"<b>Occupant ID:</b> {target['occupant_id']}<br>"
            f"<b>Name:</b> {target.get('name', 'Unknown')}<br>"
            f"<b>Medical Urgency:</b> {target['medical_urgency_score']:.1f}%<br>"
            f"<b>Coordinates:</b> X={x:.2f}, Y={y:.2f}, Z={z:.2f}<br>"
            f"<b>Location Confidence:</b> {target['location_confidence']}"
        )

    fig.add_trace(
        go.Scatter3d(
            x=x_values,
            y=y_values,
            z=z_values,
            mode="markers+text",
            text=[
                f"{target['occupant_id']}<br>({x:.1f}, {y:.1f}, {z:.1f})"
                for target, x, y, z in zip(targets, x_values, y_values, z_values)
            ],
            textposition="top center",
            hovertext=hover_text,
            hoverinfo="text",
            marker={
                "size": marker_sizes,
                "color": urgency_scores,
                "colorscale": [
                    [0.00, "#16a34a"],
                    [0.40, "#22c55e"],
                    [0.60, "#f59e0b"],
                    [0.80, "#f97316"],
                    [1.00, "#dc2626"],
                ],
                "cmin": 0,
                "cmax": 100,
                "opacity": 0.92,
                "line": {"color": "rgba(255, 255, 255, 0.9)", "width": 2},
                "colorbar": {"title": "Medical<br>Urgency", "ticksuffix": "%"},
            },
            name="Trapped occupants",
        )
    )

    x0, x1, y0, y1, z0, z1 = _building_footprint(bim_data)
    fig.update_layout(
        title="Machon Tal Beit HaDfus 7: Live USAR 3D Fusion Dashboard",
        scene={
            "xaxis": {"title": "Campus X meters", "range": [x0, x1]},
            "yaxis": {"title": "Campus Y meters", "range": [y0, y1]},
            "zaxis": {"title": "Floor height Z meters", "range": [z0, z1]},
            "aspectmode": "manual",
            "aspectratio": {"x": 1.35, "y": 0.9, "z": 0.72},
            "camera": {"eye": {"x": 1.45, "y": 1.65, "z": 1.05}},
        },
        margin={"l": 0, "r": 0, "t": 48, "b": 0},
        paper_bgcolor="#ffffff",
        uirevision="machon-tal-static-camera",
    )
    return fig


def build_figure(targets, bim_data=None, live_devices=None):
    fig = go.Figure(build_static_figure(targets, bim_data).to_dict())
    add_live_ble_devices(fig, live_devices or [])
    return fig