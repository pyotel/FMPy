import unittest
from fmpy.examples.coupled_clutches import simulate_coupled_clutches
from fmpy import CO_SIMULATION, MODEL_EXCHANGE, platform

class ExamplesTest(unittest.TestCase):

    def test_coupled_clutches_example(self):


        if platform.startswith('win'):
            fmi_versions = ['1.0', '2.0']
        elif platform.startswith('linux'):
            fmi_versions = ['2.0']
        else:
            self.fail('Platform not supported')

        for fmi_version in fmi_versions:
            for fmi_type in [CO_SIMULATION, MODEL_EXCHANGE]:
                simulate_coupled_clutches(fmi_version=fmi_version, fmi_type=fmi_type, show_plot=False)

        # TODO: add assertions


if __name__ == '__main__':

    unittest.main()