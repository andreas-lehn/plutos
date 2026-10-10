import unittest

from marketdata import Histogram

# sample data for 28.09.226
#
#   open,  high,  low,  close, histo
# 122622,122656,122615,122652,"[3, 10, 3, 7, 11, 7, 5, 29, 4, 3, 2, 2, 16, 4, 3, 3, 2, 3, 4, 3, 1, 7, 3, 5, 8, 8, 3, 3, 4, 3, 6, 6, 1, 7, 3, 3, 6, 4, 4, 7, 4, 4]"
# 122652,122667,122644,122666,"[4, 12, 9, 1, 9, 6, 5, 15, 9, 9, 16, 8, 8, 6, 0, 7, 6, 5, 2, 7, 4, 4, 3, 2]"
# 122662,122675,122659,122675,"[12, 8, 5, 3, 7, 6, 15, 6, 3, 1, 2, 3, 1, 2, 1, 0, 1]"
# 122676,122679,122654,122666,"[17, 8, 8, 6, 0, 26, 8, 7, 7, 10, 6, 21, 14, 8, 1, 4, 6, 2, 4, 1, 0, 5, 2, 5, 1, 2]"
# 122664,122669,122661,122662,"[8, 8, 11, 7, 25, 14, 8, 2, 5]"
# 122661,122665,122654,122654,"[18, 8, 8, 6, 2, 26, 9, 9, 8, 11, 7, 27]"
# 122660,122660,122654,122658,"[19, 10, 8, 6, 4, 26, 10]"
# 122654,122667,122654,122667,"[20, 10, 8, 6, 5, 28, 11, 12, 10, 11, 7, 27, 15, 10]"
# 122662,122671,122662,122669,"[11, 11, 8, 28, 17, 10, 4, 8, 8, 3]"


class TestHistogram(unittest.TestCase):
    def test_init_and_access(self):
        histo = Histogram(122659, [12, 8, 5, 3, 7, 6, 15, 6, 3, 1, 2, 3, 1, 2, 1, 0, 1])
        self.assertEqual(histo.low, 122659)
        self.assertEqual(histo.high, 122675)
        self.assertEqual(histo[histo.low - 1], 0)
        self.assertEqual(histo[histo.low], 12)
        self.assertEqual(histo[histo.low + 1], 8)
        self.assertEqual(histo[histo.high - 3], 2)
        self.assertEqual(histo[histo.high], 1)
        self.assertEqual(histo[histo.high + 1], 0)

    # 2. Test: Greift der TypeError bei falschen Datentypen?
    def test_init_validation_error(self):
        # Wir erwarten, dass ein TypeError geworfen wird
        with self.assertRaises(TypeError):
            Histogram(30170.25, [12, 8, 5, 3, 7, 6, 15, 6, 3, 1, 2, 3, 1, 2, 1, 0, 1])
            Histogram(122659, 122675)
            Histogram(122659, [10, "Hallo", 30])

    def test_assign_error(self):
        obj = Histogram(1, [1, 2, 3])
        with self.assertRaises(TypeError):
            obj[1] = 2.5  # Floats sind verboten
        with self.assertRaises(IndexError):
            obj[0] = 0
            obj[4] = 2

    def test_validation_value_error(self):
        with self.assertRaises(ValueError):
            Histogram(5, [10, -5, 30])

    def test_iterator(self):
        obj = Histogram(5, [10, 0, 20])
        ergebnis = list(obj)  # Macht aus dem Generator wieder eine Liste von Paaren

        # Erwartet werden Paare aus (Index, Wert)
        selbst_erwartet = [(5, 10), (7, 20)]
        self.assertEqual(ergebnis, selbst_erwartet)

    def test_loeschen_verboten(self):
        obj = Histogram(5, [1, 2, 3])
        with self.assertRaises(TypeError):
            del obj[6]

    def test_addition(self):
        a = Histogram(1, [1, 2, 3, 4])
        b = Histogram(3, [2, 1, 4, 3])
        c = a + b

        self.assertEqual(list(c), [(1, 1), (2, 2), (3, 5), (4, 5), (5, 4), (6, 3)])
        # Testen, ob 'a' unverändert und unabhängig blieb (kein geteilter Speicher!)
        self.assertEqual(list(a), [(1, 1), (2, 2), (3, 3), (4, 4)])
        self.assertEqual(list(b), [(3, 2), (4, 1), (5, 4), (6, 3)])

    def test_iadd(self):
        a = Histogram(1, [1, 2, 3, 4])
        b = Histogram(3, [2, 1, 4, 3])
        c = a + b
        a += b
        self.assertEqual(a._values, c._values)
        self.assertEqual(list(b), [(3, 2), (4, 1), (5, 4), (6, 3)])

    def test_volume(self):
        a = Histogram(1, [1, 2, 3, 4])

        self.assertEqual(a.volume, 10)
        a[1] = 0
        self.assertEqual(a.volume, 9)

        b = Histogram(2, [4, 6])
        a.merge(b)
        self.assertEqual(a.volume, 19)

    def test_average(self):
        a = Histogram(2, [2, 3, 1])
        self.assertEqual(a.average, 3)

        a[4] = 0
        a[2] = 5
        self.assertEqual(a.average, 2)

        a.merge(Histogram(3, [4]))
        self.assertEqual(a.average, 3)


# Dieser Block sorgt dafür, dass die Tests starten, wenn man die Datei direkt ausführt
if __name__ == "__main__":
    unittest.main()
