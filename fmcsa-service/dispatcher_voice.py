from __future__ import annotations

from dataclasses import dataclass

from dispatcher_models import LanguageCode


SPANISH_HINTS = {
    "carga",
    "camion",
    "camión",
    "mejor",
    "cerca",
    "actualiza",
    "ruta",
    "hoy",
    "gracias",
}
PUNJABI_HINTS = {
    "sat",
    "sri",
    "akaal",
    "punjabi",
    "veer",
    "kida",
    "load",
    "changa",
    "haanji",
}


@dataclass
class ParsedVoiceIntent:
    language: LanguageCode
    intent: str
    entities: dict[str, str]
    requires_confirmation: bool


def detect_language(text: str) -> LanguageCode:
    lowered = text.lower()
    if any(token in lowered for token in SPANISH_HINTS):
        return LanguageCode.es
    if any(token in lowered for token in PUNJABI_HINTS):
        return LanguageCode.pa
    return LanguageCode.en


def parse_intent(text: str) -> ParsedVoiceIntent:
    lowered = text.lower()
    language = detect_language(lowered)

    if "best load" in lowered or "mejor carga" in lowered or "load near me" in lowered:
        return ParsedVoiceIntent(
            language=language,
            intent="get_best_load",
            entities={},
            requires_confirmation=False,
        )

    if "preferred lane" in lowered or "update my lane" in lowered or "actualiza mi ruta" in lowered:
        # Minimal entity extraction for MVP.
        origin = "current_region"
        destination = "chicago" if "chicago" in lowered else "unknown"
        return ParsedVoiceIntent(
            language=language,
            intent="update_preferred_lane",
            entities={"origin_region": origin, "destination_region": destination},
            requires_confirmation=True,
        )

    return ParsedVoiceIntent(
        language=language,
        intent="unknown",
        entities={},
        requires_confirmation=False,
    )


def confirmation_prompt(language: LanguageCode, destination: str) -> str:
    if language == LanguageCode.es:
        return f"Confirmo: quieres actualizar tu ruta preferida hacia {destination}. Responde si o no."
    if language == LanguageCode.pa:
        return f"Main confirm kar reha haan: tusi preferred lane {destination} karni hai? Haan ya na bolo."
    return f"Just to confirm: you want to update your preferred lane to {destination}. Please say yes or no."
