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
