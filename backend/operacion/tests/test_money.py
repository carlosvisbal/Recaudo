from decimal import Decimal

from operacion.money import format_cop, money, numero_a_letras


def test_money_no_usa_flotantes():
    assert money("1500000.1") == Decimal("1500000.10")
    assert money(Decimal("10.005")) == Decimal("10.01")
    assert str(money("99.99")) == "99.99"


def test_format_cop_colombiano():
    assert format_cop(Decimal("1500000")) == "$1.500.000,00"
    assert format_cop("2500.5") == "$2.500,50"


def test_numero_a_letras_casos():
    assert numero_a_letras(1).startswith("UN PESO")
    assert "VEINTIUNO" in numero_a_letras(21)
    assert "CIEN PESOS" in numero_a_letras(100)
    assert "CIENTO UNO" in numero_a_letras(101)
    assert numero_a_letras(1000).startswith("MIL PESOS")
    assert "UN MILLON" in numero_a_letras(1_000_000)
    assert "QUINIENTOS MIL" in numero_a_letras(500_000)
    assert "M/CTE" in numero_a_letras(1500000)
    assert "CON 50/100" in numero_a_letras(Decimal("10.50"))
