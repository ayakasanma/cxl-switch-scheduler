from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import run_cgof_power_cohort as cohort


class CohortTests(unittest.TestCase):
    def test_only_remaining_frozen_cases(self):
        self.assertEqual(len(cohort.CASES), 11)
        self.assertEqual(len(set(cohort.CASES)), 11)
        self.assertNotIn((1, 509, 'A'), cohort.CASES)
        self.assertEqual(cohort.CASES[0], (1, 510, 'A'))
        self.assertEqual(set(cohort.CASES) | {(1, 509, 'A')},
                         {(weight, seed, arm) for weight in (1, 2) for seed in (509, 510, 511) for arm in ('A', 'B')})

    def test_package_retains_frozen_source_and_mapped_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'case'
            logs = Path(temporary) / 'logs'
            directory.mkdir()
            logs.mkdir()
            for name in ('metadata.json', 'audit.json', 'vectors.txt.gz'):
                (directory / name).write_bytes(b'fixture')
            frozen = {'scripts/runner.py': b'frozen source', 'mapped/output/top.v': b'mapped bytes'}
            with zipfile.ZipFile(directory / 'source-freeze.zip', 'w') as archive:
                for name, data in frozen.items():
                    archive.writestr(name, data)
            with patch.object(cohort, 'LOG', logs):
                result = cohort.package(directory)
                with tarfile.open(result) as archive:
                    self.assertEqual(len(archive.getnames()), len(set(archive.getnames())))
                    for name, data in frozen.items():
                        self.assertEqual(archive.extractfile(name).read(), data)
                with self.assertRaises(FileExistsError):
                    cohort.package(directory)


if __name__ == '__main__':
    unittest.main()
