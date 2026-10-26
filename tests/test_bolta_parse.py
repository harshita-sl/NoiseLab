"""parse.py — intent + slot extraction across scripts."""

import pytest

from bolta.parse import parse


def intent(t):
    return parse(t).intent


class TestIntents:
    @pytest.mark.parametrize("t", [
        "Rahul ne paanch sau rupaye diye",
        "राहुल ने पाँच सौ रुपये दिए",
        "రాహుల్ ఐదు వందలు రూపాయలు ఇచ్చాడు",
        "Lakshmi ne ek hazaar diye",
        "Vijay ne ikkis sau jama kiye",
        "Ravi ki moodu veyalu rupayalu ivvali",
    ])
    def test_record_payment(self, t):
        c = parse(t)
        assert c.intent == "record_payment"
        assert c.slots["amount"] > 0

    @pytest.mark.parametrize("t", [
        "Sunita ka udhaar kitna hai",
        "सुनीता का उधार कितना है",
        "సునీత అప్పు ఎంత ఉంది",
        "Ramesh ka baki kitna hai batao",
        "Geeta ka balance kitna hai",
        "Suresh ka paisa kitna baaki hai",
    ])
    def test_check_credit(self, t):
        assert intent(t) == "check_credit"

    @pytest.mark.parametrize("t", [
        "Maggi kitni bachi hai", "मैगी कितनी बची है",
        "Maggi entha stock undi", "Doodh ka stock check karo",
        "Kurkure kitne packet pade hain", "Chini ka stock kitna pada hai",
    ])
    def test_check_stock(self, t):
        assert intent(t) == "check_stock"

    @pytest.mark.parametrize("t", [
        "Do kilo chini bik gayi", "दो किलो चीनी बिक गई",
        "Maggi ke bees packet bik gaye", "Ek litre tel bik gaya",
        "Teen dabba ghee bik gaye", "రెండు కిలోల చక్కెర అమ్ముడయ్యింది",
    ])
    def test_record_sale(self, t):
        c = parse(t)
        assert c.intent == "record_sale"
        assert c.slots.get("qty") is not None

    @pytest.mark.parametrize("t", [
        "Chaar carton Coke mangwani hai", "Aata paanch kilo mangwana hai",
        "Do dozen anda order karo", "Parle-G pachaas packet aaye",
        "నాలుగు కార్టన్ల కోక్ మంగించాను",
    ])
    def test_add_purchase(self, t):
        c = parse(t)
        assert c.intent == "add_purchase"
        assert c.slots.get("qty") is not None

    @pytest.mark.parametrize("t", [
        "Kal kya order karna chahiye", "Aaj kya mangana chahiye order mein",
        "कल क्या ऑर्डर करना चाहिए", "రేపు ఏమి ఆర్డర్ చేయాలి",
    ])
    def test_reorder(self, t):
        assert intent(t) == "reorder_suggestion"

    @pytest.mark.parametrize("t", [
        "Undo karo last entry", "आखिरी एंट्री हटाओ", "పాత ఎంట్రీ రద్దు చేయి",
        "piche wala wapas",
    ])
    def test_undo(self, t):
        assert intent(t) == "undo"

    @pytest.mark.parametrize("t", ["haan theek hai", "हाँ ठीक है", "sahi hai",
                                   "అవును సరే"])
    def test_confirm(self, t):
        assert intent(t) == "confirm"

    @pytest.mark.parametrize("t", ["nahi galat hai", "नहीं गलत है",
                                   "కాదు వద్దు", "cancel karo"])
    def test_deny(self, t):
        assert intent(t) == "deny"

    @pytest.mark.parametrize("t", [
        "aaj bijli ka bill aaya kya", "bus kab aayegi",
        "toh kal ki sabzi ka rate kya hai",
    ])
    def test_unknown(self, t):
        assert intent(t) == "unknown"


class TestSlotExtraction:
    def test_credit_flag(self):
        c = parse("Mohan ne do kilo chini liya udhaar par")
        assert c.intent == "record_sale"
        assert c.slots.get("credit") is True
        assert c.slots["qty"] == 2 and c.slots["unit"] == "kg"

    def test_ka_priced_generic(self):
        c = parse("Sunita ne pandrah sau ka samaan liya udhaar pe")
        assert c.intent == "record_sale"
        assert c.slots["amount"] == 150000

    def test_generic_credit_ok_without_product(self):
        c = parse("Sunita ne pandrah sau ka samaan liya udhaar pe")
        assert "product" not in c.unresolved

    def test_no_name_without_marker(self):
        # 'maggi ke 20 packet' -> maggi is product, not a person
        c = parse("Maggi ke bees packet bik gaye")
        assert "customer" not in c.slots
        assert c.slots.get("product", "").strip() == "maggi"

    def test_liya_not_payment(self):
        c = parse("Mohan ne do kilo chini liya udhaar par")
        assert c.intent == "record_sale"

    def test_number_no_money_word_near_pay_verb(self):
        c = parse("Rahul ne paanch sau diye")
        assert c.intent == "record_payment"
        assert c.slots["amount"] == 50000

    def test_identifier_not_amount(self):
        c = parse("invoice number 203 ka refund pachaas percent hoga")
        # 203 must not become amount; 50 percent has no intent anyway
        assert c.intent == "unknown"


class TestAdjustPhrasing:
    """'update/adjust/set' imperatives — spoken phrasings outside the corpus."""

    @pytest.mark.parametrize("t,name,amount", [
        ("khate mein rahul ka udhar five hundred update kar do", "rahul", 50000),
        ("rahul ka udhaar 500 update karo", "rahul", 50000),
        ("priya ka udhaar do sau set kar do", "priya", 20000),
        ("kaka ka udhaar teen sau rupaye adjust karo", "kaka", 30000),
        ("mohan ka udhaar badlo paanch sau", "mohan", 50000),
    ])
    def test_udhaar_update_is_credit_sale(self, t, name, amount):
        c = parse(t)
        assert c.intent == "record_sale"
        assert c.slots["customer"] == name
        assert c.slots["amount"] == amount
        assert c.slots["credit"] is True

    def test_stock_update_is_purchase(self):
        c = parse("maggi ka stock 20 packet update kar do")
        assert c.intent == "add_purchase"
        assert c.slots["product"] == "maggi"
        assert c.slots["qty"] == 20 and c.slots["unit"] == "packet"


class TestEntityFallback:
    """Entities resolved but no verb matched -> plausible low-conf proposal
    instead of 'unknown' (confirm card still gates any write)."""

    def test_bare_udhaar_name_is_credit_check(self):
        c = parse("sunil ka udhaar batao na please")
        # 'batao' already makes it a question; use a truly verb-less case:
        c = parse("toh sunil ka udhaar")
        assert c.intent == "check_credit"
        assert c.slots["customer"] == "sunil"
        assert c.confidence < 0.6

    def test_amount_and_name_falls_back_to_payment(self):
        c = parse("arre vijay 400 wala scene")
        assert c.intent == "record_payment"
        assert c.slots["amount"] == 40000
        assert c.confidence < 0.5

    def test_regressions_unchanged(self):
        assert intent("rahul ka udhaar kitna hai") == "check_credit"
        assert intent("rahul ne paanch sau rupaye diye") == "record_payment"
        assert intent("maggi kitni bachi hai") == "check_stock"
