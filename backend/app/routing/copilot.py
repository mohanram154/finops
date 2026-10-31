from typing import List, Dict, Any, Optional

class RoutingCopilot:
    """
    Explains routing decisions in clear, human-understandable natural language.
    Answers 'Why did you choose this model?' dynamically from actual routing data.
    """

    @classmethod
    def generate_explanation(
        cls,
        selected_model: str,
        selected_quality: float,
        selected_cost: float,
        selected_latency_ms: float,
        required_quality: float,
        reasons: List[str],
        rejected_models: List[Dict[str, Any]],
        alternatives: List[Dict[str, Any]],
        budget_remaining: float,
        currency: str = "₹",
        historical_quality: Optional[float] = None,
        historical_success_rate: Optional[float] = None
    ) -> str:
        model_upper = selected_model.upper()
        lines = [f"WHY {model_upper}?\n"]

        # Quality constraint statement
        lines.append(f"✓ Required quality: {int(required_quality) if required_quality.is_integer() else required_quality}")
        lines.append(f"✓ {selected_model.capitalize()} quality: {int(selected_quality) if selected_quality.is_integer() else selected_quality}")

        if historical_quality is not None and historical_success_rate is not None:
            lines.append(f"✓ Historical task performance: {historical_quality}% quality with {historical_success_rate}% success rate")

        # Explain why cheaper/rejected models were dropped
        for rej in rejected_models:
            m_name = rej.get("model", "").capitalize()
            q = rej.get("quality", 0)
            reason = rej.get("reason", "")
            if "quality" in reason.lower():
                lines.append(f"✓ {m_name} quality: {int(q) if isinstance(q, float) and q.is_integer() else q}, therefore rejected")
            elif "latency" in reason.lower():
                lines.append(f"✓ {m_name} latency exceeded constraint, therefore rejected")
            elif "budget" in reason.lower():
                lines.append(f"✓ {m_name} exceeded remaining budget, therefore rejected")

        # Explain alternatives that were qualified but more expensive
        if alternatives:
            more_expensive = [a for a in alternatives if a.get("cost", 0) > selected_cost]
            for alt in more_expensive:
                alt_name = alt.get("model", "").capitalize()
                alt_q = alt.get("quality", 0)
                formatted_q = int(alt_q) if isinstance(alt_q, (int, float)) and float(alt_q).is_integer() else alt_q
                lines.append(f"✓ {alt_name} quality: {formatted_q} but costs more")

        # Latency and budget confirmations
        lines.append("✓ Latency requirement satisfied")
        lines.append("✓ Budget available\n")

        # Cost statement
        lines.append("Estimated cost:")
        lines.append(f"{currency}{selected_cost:.4f}" if selected_cost < 0.01 else f"{currency}{selected_cost:.2f}")

        # Calculate savings compared to the most expensive valid alternative or tier
        if alternatives:
            highest_cost_alt = max(a.get("cost", 0) for a in alternatives)
            if highest_cost_alt > selected_cost:
                saving = highest_cost_alt - selected_cost
                alt_name = next(a.get("model", "") for a in alternatives if a.get("cost", 0) == highest_cost_alt)
                lines.append(f"\nEstimated saving compared with {alt_name.capitalize()}:")
                lines.append(f"{currency}{saving:.4f}" if saving < 0.01 else f"{currency}{saving:.2f}")

        return "\n".join(lines)

    @classmethod
    def generate_failure_explanation(
        cls,
        required_quality: float,
        rejected_models: List[Dict[str, Any]],
        remaining_budget: float,
        currency: str = "₹"
    ) -> str:
        lines = [
            "ROUTING CONSTRAINT FAILURE: NO MODEL SATISFIES REQUIREMENTS\n",
            f"Target Quality Threshold: {required_quality}",
            f"Remaining Budget: {currency}{remaining_budget:.2f}\n",
            "Evaluated Model Candidates:"
        ]
        for rej in rejected_models:
            lines.append(f"✗ {rej.get('model', '').capitalize()}: {rej.get('reason', 'Failed constraints')}")

        lines.append("\nRecommendation:")
        lines.append("- Relax the required quality threshold or increase the departmental budget allocation.")
        return "\n".join(lines)
