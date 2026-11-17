    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Processed records",
        f"{record_count:,}" if record_count is not None else "Unavailable",
    )
    metric_columns[1].metric(
        "Equipment",
        f"{equipment_count:,}" if equipment_count is not None else "Unavailable",
    )
    metric_columns[2].metric(
        "Average latest RUL",
        f"{average_rul:.2f} cycles" if average_rul is not None else "Unavailable",
    )
    metric_columns[3].metric("Model features", feature_count or "Unavailable")
    st.caption(
        f"MongoDB: {database_status}"
        + (f" · Database: {database_name}" if database_name else "")
    )

    if latest is not None:
        health_counts = latest["health_status"].value_counts().reindex(
            ["Critical", "Warning", "Monitor", "Healthy"], fill_value=0
        )
        risk_counts = latest["risk_category"].value_counts().reindex(
            ["High", "Elevated", "Moderate", "Low"], fill_value=0
        )
        health_column, risk_column = st.columns(2)
        with health_column:
            st.subheader("Equipment health")
            st.bar_chart(health_counts, color="#1769E8")
        with risk_column:
            st.subheader("Equipment risk")
            st.bar_chart(risk_counts, color="#E5A12B")

    metrics_path = PROJECT_ROOT / "outputs" / "final_model_metrics.csv"
    if metrics_path.is_file():
        try:
            metrics_df = pd.read_csv(metrics_path)
            saved_metrics = {
                str(row["Metric"]): float(row["Value"])
                for _, row in metrics_df.iterrows()
                if {"Metric", "Value"}.issubset(metrics_df.columns)
            }
        except (OSError, pd.errors.ParserError, TypeError, ValueError) as error:
            st.warning(f"Saved model metrics could not be read: {error}")
        else:
            if saved_metrics:
                st.subheader("Saved validation metrics")
                columns = st.columns(len(saved_metrics))
                for column, (name, value) in zip(columns, saved_metrics.items()):
                    column.metric(name, f"{value:.3f}")
                st.caption(
                    "These are saved validation results for the existing model; "
                    "the model is not retrained on app startup."
                )

    user = st.session_state.get("user")
    if user and database_status == "Connected":
        try:
            history = get_prediction_history(
                user["id"], limit=10, include_reports=False
            )
        except (OSError, PyMongoError, RuntimeError, ValueError) as error:
            st.warning(
                "Personal prediction trends are unavailable "
                f"({type(error).__name__})."
            )
        else:
            if len(history) > 1:
                history_frame = pd.DataFrame(history)
                history_frame["prediction_timestamp"] = pd.to_datetime(
                    history_frame["prediction_timestamp"], utc=True, errors="coerce"
                )
                history_frame = history_frame.dropna(
                    subset=["prediction_timestamp"]
                ).sort_values("prediction_timestamp")
                if not history_frame.empty:
                    st.subheader("Your prediction trend")
                    st.line_chart(
                        history_frame.set_index("prediction_timestamp")[
                            "average_predicted_rul"
                        ]
                    )

    st.caption(
        "The monitoring page replays historical dataset rows. No live sensors "
        "or continuous streaming source are connected."
    )


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

auth_enabled = is_auth_enabled()
if auth_enabled and not is_mongodb_configured():
    st.error(
        "AUTH_ENABLED is true but MongoDB is not configured. Set MONGODB_URI "
        "and MONGODB_DATABASE before enabling login."
    )
    st.stop()

if auth_enabled and not (
    st.session_state.authenticated and st.session_state.user
):
    st.session_state.authenticated = False
    st.session_state.user = None
    page = st.navigation(
        [st.Page(show_authentication, title="Login", default=True)],
        position="hidden",
    )
else:
    if not auth_enabled:
        st.session_state.authenticated = False
        st.session_state.user = None
    page = st.navigation(
        [st.Page(show_dashboard, title="Predictive Maintenance", default=True)],
        position="hidden",
    )

page.run()
