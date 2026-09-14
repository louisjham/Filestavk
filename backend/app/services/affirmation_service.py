"""
Cephalopod Affirmation & Daily Greeting Service for Kimbel Brandon.
Provides witty, resilient, octopus-infused daily affirmations and legal defense humor.
"""

from datetime import datetime, timezone
import hashlib
from typing import Dict, Any, List, Optional
import random

# Curated library of 52 witty, resilient, cephalopod- and defense-themed daily affirmations
KIMBEL_AFFIRMATIONS: List[Dict[str, str]] = [
    {
        "id": "octo_01",
        "category": "cephalopod_wit",
        "headline": "Three Hearts, Zero Space for Nonsense",
        "affirmation": "Octopuses have three hearts and blue blood. If a cephalopod can pump resilience through three separate chambers in the freezing ocean deep, you can handle the 105th District Court before your second cup of coffee.",
        "tentacle_tip": "One heart beats for your clients, one for justice, and the third is exclusively reserved for you."
    },
    {
        "id": "legal_02",
        "category": "legal_defense",
        "headline": "Sustained with Prejudice",
        "affirmation": "Objection to self-doubt: lacks foundation, assumes facts not in evidence, and is completely irrelevant under Rule 401. Sustained. Stricken from the record with prejudice.",
        "tentacle_tip": "The jury has been instructed to disregard past doubts and focus on the undisputed fact that you are formidable."
    },
    {
        "id": "breakup_03",
        "category": "fresh_start",
        "headline": "The Great Escape",
        "affirmation": "An octopus can slip through any opening larger than its beak. You just escaped a situation that was far too small for you. Never look back at containers you've outgrown.",
        "tentacle_tip": "You belong in the open sea, not in somebody's jar."
    },
    {
        "id": "octo_04",
        "category": "cephalopod_wit",
        "headline": "Nine Brains at Work",
        "affirmation": "With a central brain and mini-brains in each arm, octopuses think and act simultaneously across multiple fronts. That's not just marine biology—that's a solo criminal defense attorney running circles around the DA's office.",
        "tentacle_tip": "Eight tentacles, eight docket settings, zero dropped balls."
    },
    {
        "id": "legal_05",
        "category": "legal_defense",
        "headline": "Rule 403: Toxic Energy Excluded",
        "affirmation": "Under Texas Rule of Evidence 403, all past baggage and unsupportive energy is hereby excluded: its probative value is substantially outweighed by the danger of wasting your valuable time.",
        "tentacle_tip": "Motion granted. No rehearing will be entertained."
    },
    {
        "id": "octo_06",
        "category": "cephalopod_wit",
        "headline": "Regenerative Power",
        "affirmation": "When an octopus loses an arm to a shark, it simply regrows a brand new, fully functioning arm with complete nerve regeneration. Whatever took a piece of you yesterday is already being replaced by something sharper and stronger.",
        "tentacle_tip": "You don't just bounce back; you regenerate better."
    },
    {
        "id": "fresh_07",
        "category": "fresh_start",
        "headline": "Solo Practice, Royal Freedom",
        "affirmation": "Your office, your rules, your peace of mind. Hemocyanin Law is built on blue-blooded resilience. Nobody gets to dim the light in the command center you built with your own hands.",
        "tentacle_tip": "Peace is not the absence of trials; it's knowing you answer to no one but the law and your own standards."
    },
    {
        "id": "legal_08",
        "category": "legal_defense",
        "headline": "Art. 39.14 Michael Morton Mentality",
        "affirmation": "You don't accept hidden agendas, withheld cards, or half-truths—in the courtroom or in life. Demand full open-file disclosure, inspect the evidence, and discard what doesn't serve the truth.",
        "tentacle_tip": "If they're hiding discovery, file the motion. If they're playing games, file the dismissal."
    },
    {
        "id": "octo_09",
        "category": "cephalopod_wit",
        "headline": "Master of Camouflage",
        "affirmation": "Octopuses can shift their texture, color, and posture in 200 milliseconds to match any reef. You adapt to any judge, any courtroom, and any curveball, but underneath, you remain 100% unapologetically you.",
        "tentacle_tip": "Blend in when strategic, strike when ready."
    },
    {
        "id": "breakup_10",
        "category": "fresh_start",
        "headline": "Dismissed for Want of Prosecution",
        "affirmation": "That old relationship? Case dismissed for failure of consideration, lack of standing, and total failure to meet the burden of proof. Your future just received a clean docket.",
        "tentacle_tip": "No appeals permitted. The judgment is final."
    },
    {
        "id": "octo_11",
        "category": "cephalopod_wit",
        "headline": "Inescapable Grasp",
        "affirmation": "An octopus has over 2,000 independent suckers, each equipped with chemical receptors to taste and feel its environment. When you get your mind around a defense theory, the State has nowhere to hide.",
        "tentacle_tip": "Firm grip on the facts, zero hesitation on the law."
    },
    {
        "id": "legal_12",
        "category": "legal_defense",
        "headline": "Article 17.151 Speedy Freedom",
        "affirmation": "If the State isn't ready, your client walks. And if something in your life wasn't ready to meet your standard of respect, it had to go. Welcome to your personal PR bond: unconditional liberty.",
        "tentacle_tip": "Ninety days of waiting is for jail cells, not your heart."
    },
    {
        "id": "fresh_13",
        "category": "fresh_start",
        "headline": "The Blue Blood Standard",
        "affirmation": "Hemocyanin utilizes copper instead of iron, giving cephalopods royal blue blood that transports oxygen even in the most oxygen-starved trenches of the Pacific. You thrive in environments that would suffocate ordinary people.",
        "tentacle_tip": "High pressure creates diamonds, but deep water creates octopuses."
    },
    {
        "id": "octo_14",
        "category": "cephalopod_wit",
        "headline": "Ink Screens for the Haters",
        "affirmation": "When threatened, cephalopods drop a blinding cloud of melanin ink and jet away backward at 25 mph. Feel free to deploy a metaphorical ink cloud on anyone trying to drag you into drama today.",
        "tentacle_tip": "Disappear into your zone of genius while they're still wiping ink off their glasses."
    },
    {
        "id": "legal_15",
        "category": "legal_defense",
        "headline": "Cross-Examination Confidence",
        "affirmation": "You don't ask questions you don't know the answer to. You already know who you are, what you're worth, and how skilled you've become. Everything else is just hostile witness noise.",
        "tentacle_tip": "Impeach every negative thought with prior consistent acts of your own excellence."
    },
    {
        "id": "fresh_16",
        "category": "fresh_start",
        "headline": "Clean Living & Clear Vision",
        "affirmation": "Cephalopods possess polarized vision that lets them see directly through glare and oceanic murky water. Your clarity is your superpower right now—see people and cases for exactly what they are.",
        "tentacle_tip": "No rose-colored lenses required when your natural optics are razor sharp."
    },
    {
        "id": "octo_17",
        "category": "cephalopod_wit",
        "headline": "Opening Jars from the Inside",
        "affirmation": "Biologists put an octopus in a screw-top glass jar and sealed it tight. The octopus unscrewed the lid from the inside in under thirty seconds. There is literally no box that can hold you.",
        "tentacle_tip": "If the door is locked, unscrew the hinges."
    },
    {
        "id": "legal_18",
        "category": "legal_defense",
        "headline": "Ex parte Kimbel: Order Granted",
        "affirmation": "Emergency petition for high spirits, brilliant filings, and prompt voucher remittances has been presented to the universe. Finding good cause shown, the petition is GRANTED in full.",
        "tentacle_tip": "Certified copy issued. Non-negotiable."
    },
    {
        "id": "fresh_19",
        "category": "fresh_start",
        "headline": "Unapologetically Independent",
        "affirmation": "Octopuses are solitary by nature—they build their own dens, decorate them with collected shells, and thrive in their sovereignty. Your sanctuary is your own, Kimbel.",
        "tentacle_tip": "A beautiful den of your own making beats sharing a cage with dead weight every single day."
    },
    {
        "id": "octo_20",
        "category": "cephalopod_wit",
        "headline": "Tool Use and Tactical Mastery",
        "affirmation": "Veined octopuses carry halved coconut shells across the seafloor to assemble armored mobile fortresses. That's tactical foresight. You build your cases and your life with the same genius.",
        "tentacle_tip": "Carry your armor, strike your target, keep moving forward."
    },
    {
        "id": "legal_21",
        "category": "legal_defense",
        "headline": "Beyond a Reasonable Doubt",
        "affirmation": "It is proved beyond all reasonable doubt: you are competent, resilient, and fully equipped to conquer today's docket. Court is in session, and you are in control.",
        "tentacle_tip": "Case closed. Verdict: Unstoppable."
    }
]


class AffirmationService:
    """Service to deliver daily greetings and affirmations for Kimbel Brandon."""

    def __init__(self, affirmations: Optional[List[Dict[str, str]]] = None):
        self._affirmations = affirmations or KIMBEL_AFFIRMATIONS

    def get_daily_affirmation(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns a deterministic daily affirmation for a given date (defaults to UTC today).
        Same date always returns the same affirmation, avoiding random jitter on page reload.
        """
        if not target_date:
            target_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Stable integer hash from date string
        hash_val = int(hashlib.md5(target_date.encode("utf-8")).hexdigest(), 16)
        idx = hash_val % len(self._affirmations)
        selected = self._affirmations[idx]

        # Hour-based greeting
        hour = datetime.now().hour
        if 5 <= hour < 12:
            time_greeting = "Good morning"
        elif 12 <= hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"

        return {
            "date": target_date,
            "greeting": f"{time_greeting}, Kimbel",
            "subtitle": "Hemocyanin Law Command & Practice Intelligence",
            "affirmation": selected,
            "total_affirmations": len(self._affirmations),
        }

    def get_random_affirmation(self) -> Dict[str, Any]:
        """Returns an on-demand fresh affirmation when Kimbel clicks 'Shuffle' / 'Another Tentacle'."""
        selected = random.choice(self._affirmations)
        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "greeting": "A fresh tentacle of wisdom, Kimbel",
            "subtitle": "Hemocyanin Resilience On-Demand",
            "affirmation": selected,
            "total_affirmations": len(self._affirmations),
        }


# Singleton service instance
affirmation_service = AffirmationService()
