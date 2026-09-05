with e_c5:
    try:
        exam_date = datetime.strptime(
            ex["Exam date"],
            "%d %B, %Y"
        ).date()

        days_left = (
            exam_date
            - now_bd.date()
        ).days

        if days_left > 0:
            st.markdown(
                f"🟢 **{days_left} days**"
            )
        elif days_left == 0:
            st.markdown(
                "🔴 **Today!**"
            )
        else:
            st.markdown(
                "⚫ **Expired**"
            )
    except Exception:
        st.caption("N/A")
