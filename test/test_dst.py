import unittest
import sys
sys.path.append('../')
from algorithmNewPoint import dst

class TestdstFunction(unittest.TestCase):
    def test_dst(self):
    	(test_x, test_y) =  dst(46.59103, 5.46573, 81, 2)
        self.assertAlmostEqual(test_x, 46.5938408, places=7)
        self.assertAlmostEqual(test_y, 5.49158256, places=7)

    def test_dst_negatif(self):
    	(test_x, test_y) =  dst(-53.15056, -1.84444, 20, 50)
        self.assertAlmostEqual(test_x, -52.7277448, places=7)
        self.assertAlmostEqual(test_y, -1.59049155, places=7)

    def test_dst_negatif(self):
    	(test_x, test_y) =  dst(-53.15056, -1.84444, 20, 50)
        self.assertAlmostEqual(test_x, -52.7277448, places=7)
        self.assertAlmostEqual(test_y, -1.59049155, places=7)

    @unittest.expectedFailure
    def test_dst_fail(self):
    	(test_x, test_y) =  dst(ABC, DEF, GH, IJ)
        self.assertAlmostEqual(test_x, -52.7277448, places=7)
        self.assertAlmostEqual(test_y, -1.59049155, places=7)

if __name__ == '__main__':
    unittest.main()
