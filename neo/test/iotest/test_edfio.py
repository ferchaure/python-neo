"""
Tests of neo.io.edfio
"""

import unittest
import numpy as np
import quantities as pq

from neo.io.edfio import EDFIO
from neo.test.iotest.common_io_test import BaseTestIO
from neo.io.proxyobjects import AnalogSignalProxy
from neo import AnalogSignal


class TestEDFIO(BaseTestIO, unittest.TestCase, ):
    ioclass = EDFIO
    entities_to_download = ['edf']
    entities_to_test = [
        'edf/edf+C.edf',
    ]

    def setUp(self):
        super().setUp()
        filename = self.get_local_path('edf/edf+C.edf')
        self.io = EDFIO(filename)

    def test_read_block(self):
        """
        Test reading the complete block and general annotations
        """
        bl = self.io.read_block()
        self.assertTrue(bl.annotations)

    def test_read_segment_lazy(self):
        """
        Test lazy loading of object structure and loading of data in a 2nd step
        """
        seg = self.io.read_segment(lazy=True)
        for ana in seg.analogsignals:
            assert isinstance(ana, AnalogSignalProxy)
            ana = ana.load()
            assert isinstance(ana, AnalogSignal)

        seg = self.io.read_segment(lazy=False)
        for anasig in seg.analogsignals:
            assert isinstance(ana, AnalogSignal)
            self.assertTrue(any(anasig.shape))

        assert seg.name == 'Seg #0 Block #0'
        for anasig in seg.analogsignals:
            assert anasig.name is not None

    def test_read_segment_with_time_slice(self):
        """
        Test loading of a time slice and check resulting times
        """
        seg = self.io.read_segment(time_slice=None)

        self.assertEqual(len(seg.spiketrains), 0)
        self.assertEqual(len(seg.events), 0)
        for asig in seg.analogsignals:
            self.assertEqual(asig.shape[0], 256)
        n_channels = sum(a.shape[-1] for a in seg.analogsignals)
        self.assertEqual(n_channels, 5)

        t_start, t_stop = 500 * pq.ms, 800 * pq.ms
        seg = self.io.read_segment(time_slice=(t_start, t_stop))

        self.assertAlmostEqual(seg.t_start.rescale(t_start.units), t_start, delta=5.)
        self.assertAlmostEqual(seg.t_stop.rescale(t_stop.units), t_stop, delta=5.)

    def test_compare_data(self):
        """
        Compare data from AnalogSignal with plain data stored in text file
        """

        plain_data = np.loadtxt(self.io.filename.replace('.edf', '.txt'))
        seg = self.io.read_segment(signal_group_mode='split-all')

        anasigs = seg.analogsignals

        for aidx, anasig in enumerate(anasigs):
            ana_data = anasig.magnitude.flatten()

            # reverting gain and offset conversion
            sig_dict = self.io.signal_headers[aidx]
            physical_range = sig_dict['physical_max'] - sig_dict['physical_min']
            digital_range = sig_dict['digital_max'] - sig_dict['digital_min']
            gain = physical_range / digital_range
            offset = -1 * sig_dict['digital_min'] * gain + sig_dict['physical_min']

            ana_data = (ana_data - offset) / gain
            # allow for some floating imprecision between calculations
            np.testing.assert_array_almost_equal(ana_data, plain_data[:, aidx], decimal=2)


if __name__ == "__main__":
    unittest.main()
