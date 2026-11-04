"""Small tests for v3 hash/cohort boundaries and reproducible TeX contracts."""
import importlib.util
import contextlib
import copy
import io
import json
from pathlib import Path
import re
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location("revision_v3",Path(__file__).with_name("generate_revision_v3.py"))
g=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(g)


class RevisionV3Tests(unittest.TestCase):
    def test_disjoint_area_reconciliation_and_record_binding(self):
        supplement=json.loads((g.ROOT/g.SUPPLEMENT).read_text())
        audit=json.loads((g.ROOT/supplement['primary_disjoint_area']['results']).read_text())
        rows=g.disjoint_area_rows(audit)
        self.assertEqual([r['policy'] for r in rows],['fcfs','rr','fai-main'])
        self.assertEqual(sum(c['leaf_inventory']['leaf_count'] for c in audit['cases']),540590)
        for kind in ('area','bin','identity'):
            bad=copy.deepcopy(audit)
            if kind=='area':bad['cases'][0]['attribution']['categories']['common']['area']='1'
            elif kind=='bin':bad['cases'][0]['attribution']['categories']['extra']={'area':'0'}
            else:bad['cases'][0]['case_id']='wrong-case'
            with self.subTest(kind=kind),self.assertRaises(ValueError):g.disjoint_area_rows(bad)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'record.json').write_bytes(b'changed')
            raw={g.SUPPLEMENT:json.dumps({'record_hashes':{'record.json':'0'*64}}).encode()}
            with self.assertRaisesRegex(ValueError,'existing record hash mismatch'):g.existing_records(root,raw)

    def test_hash_guard_rejects_changed_input_before_json(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/"x.json").write_bytes(b"not JSON")
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                g.bound_bytes(root,{"x.json":"0"*64})

    def test_exact_cohort_rejects_missing_duplicate_or_rebound_p99(self):
        row=dict(seed=509,histogram={"2":100},count=100,p99=2,mean=2)
        self.assertEqual(g.cohort([row],[509])["p99"],2)
        for rows,seeds in [([row,row],[509,510]),([], [509]),([dict(row,p99=3)],[509]),([dict(row,count=99)],[509])]:
            with self.subTest(rows=rows),self.assertRaises(ValueError):g.cohort(rows,seeds)

    def test_actual_outputs_reproducible_and_coordinates_share_table_values(self):
        tex,manifest=g.render();second,other=g.render()
        self.assertEqual((tex,manifest),(second,other))
        self.assertEqual(manifest['matrix']['pass'],498)
        self.assertEqual(manifest['cohorts']['N_expansion60runs'],24)
        self.assertEqual(len(manifest['historical_results']['six_source_anchors']),6)
        supplement=manifest['existing_record_supplement']
        self.assertEqual(supplement['primary_disjoint_area']['full9_summary']['case_count'],9)
        self.assertEqual(supplement['main_sq']['claim_locators']['trace_rows'],103424)
        self.assertEqual(supplement['main_sq']['claim_locators']['requests'],2400)
        self.assertEqual(supplement['main_sq']['claim_locators']['quota_expiries'],7)
        self.assertEqual(supplement['insight_screen']['gate_result']['frozen_candidate'],'DAC2')
        for group,keys in [('formal_bridges',('result','provenance','acceptance')),('primary_disjoint_area',('results','verification','checksums')),('main_sq',('audit','acceptance','source_execution','portable_bundle')),('insight_screen',('completed','gate','acceptance','source_freeze'))]:
            for key in keys:self.assertIn(supplement[group][key],supplement['record_hashes'])
        analysis=json.loads((g.ROOT/(g.FINAL+'snapshot/analysis/analysis.json')).read_text())
        endpoints=analysis['endpoints']+analysis['conditional_dac']['endpoints']
        for arm in ('A','B'):
            actual=re.search(r'\\newcommand\{\\RevisionPninetyNine'+arm+r'\}\{([^}]+)\}',tex)[1]
            expected=[]
            for i,policy in enumerate(g.POLICIES,1):
                rows=[r for r in endpoints if r['policy']==policy and r['profile']=='trained-'+arm and r['configuration']['group'] in ('n4-confirmation','insight-confirmation')]
                expected.append(f"({i},{g.number(g.cohort(rows,range(529,549))['p99'])})")
            self.assertEqual(actual,' '.join(expected))
        for name in ('RevisionConfirmationTable','RevisionPairedCITable','RevisionNExpansionTable','RevisionPowerTable','RevisionCgofPpaTable','RevisionPrimaryAreaTable'):
            self.assertEqual(tex.count('\\newcommand{\\'+name+'}'),1)
        self.assertNotIn('\\begin{table}',tex)
        names=re.findall(r'\\newcommand\{\\([^}]+)\}',tex)
        self.assertTrue(all(re.fullmatch(r'[A-Za-z]+',name) for name in names))
        self.assertNotIn('RevisionP99',tex)
        self.assertEqual(manifest['output_tex_sha256'],g.digest(tex.encode()))
        with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
            g.main(['--out-dir',folder])
            actual=(Path(folder)/'revision_v3_results.tex').read_bytes()
            saved=json.loads((Path(folder)/'revision_v3_evidence_manifest.json').read_text())
            self.assertEqual(saved['output_tex_sha256'],g.digest(actual))
            self.assertNotIn(b'\r\n',actual)

    def test_public_policy_names_and_cgof_allocation_columns(self):
        tex,_=g.render()
        section=Path(__file__).with_name('sections').joinpath('hotnets-body-v3.tex').read_text()
        self.assertNotRegex(tex, r'\bMain\b')
        public=tex+'\n'+section
        for stale in ('DAC1','DAC2','Main-DAC','CGOF-1','CGOF-2'):
            with self.subTest(stale=stale):
                self.assertNotRegex(public,r'\b'+re.escape(stale)+r'\b')
        self.assertEqual(g.LABELS['MAIN'],'FAI-inspired')
        self.assertEqual(g.LABELS['DAC1'],'CGOF (1:1)')
        self.assertEqual(g.LABELS['DAC2'],'CGOF (2:1)')
        self.assertEqual(g.HIGH_LOW,{'DAC1':'1:1','DAC2':'2:1'})
        self.assertIn('MAIN',g.POLICIES)
        self.assertIn('DAC2',g.POLICIES)
        self.assertNotIn('credit policy is novel',section)
        for name in ('RevisionConfirmationTable','RevisionPairedCITable','RevisionCgofPpaTable'):
            marker='\\newcommand{\\'+name+'}'
            self.assertIn(marker,tex)
            block=tex.split(marker,1)[1].split('\\newcommand{',1)[0]
            self.assertIn('High:Low',block)


class ImprovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tex, cls.d = g.render_improvement()

    def test_fixed_class_uses_measurement_counts_not_drain(self):
        rows = self.d['fixed_class']
        self.assertAlmostEqual(rows[0]['shares'][0], 9999/19999)
        self.assertAlmostEqual(rows[1]['shares'][3], 4999/19999)
        self.assertEqual(g.number(rows[1]['shares'][3]*100, 4), '24.9962')
        self.assertAlmostEqual(rows[2]['shares'][0], 1/7)
        for r in rows:
            self.assertAlmostEqual(sum(r['shares']), 1)
            self.assertEqual(r['measurement_cycles'], 20000)
        self.assertEqual(rows[1]['config']['high_weight'], 1)
        self.assertEqual(rows[2]['config']['high_weight'], 2)
        self.assertTrue(all(r['config']['ordering'] == 'oldest-first' for r in rows[1:]))

    def test_finite_model_means_and_distinct_rtl_context(self):
        rows = self.d['finite_heavy']
        self.assertEqual([r['sparse_p99'] for r in rows], [28.3, 4.15, 4.85, 10, 8.7])
        self.assertEqual([r['heavy_max_gap'] for r in rows], [7, 7.55, 9.55, 7.35, 7.35])
        for r in rows:
            self.assertEqual([v['seed'] for v in r['runs']], list(range(6201, 6221)))
            self.assertEqual(r['sparse_p99'], g.mean(v['sparse_p99'] for v in r['runs']))
            self.assertTrue(all(v['classifier_boundaries'] == 0 and v['active_cycles'] < 5000000 for v in r['runs']))
        rtl = self.d['production_rtl']
        self.assertEqual([r['sparse_p99'] for r in rtl], [3, 4])
        self.assertEqual([r['heavy_max_gap'] for r in rtl], [9, 10])
        self.assertTrue(all(r['job']['profile'] == 'near' and r['job']['heavy_work'] == 5000000 for r in rtl))
        self.assertTrue(all(r['completion_ratio'] == 6248272/6248269 for r in rtl))
        self.assertTrue(all(r['effective_boundaries'] == [['High']*4] for r in rtl))

    def test_common_demand_buffer_is_still_high(self):
        self.assertEqual(g.effective_classes(['H', 'B_H', 'L', 'B_L']), ['High', 'High', 'Low', 'Low'])
        with self.assertRaisesRegex(ValueError, 'unknown Main class'):
            g.effective_classes(['Buffer'])
        for r in self.d['common_demand_rtl']:
            self.assertEqual(r['encoded_boundaries'][0], ['B_H', 'B_H', 'B_H', 'H'])
            self.assertEqual(r['effective_boundaries'], [['High']*4]*3)
            self.assertEqual(r['measurement_fires'], [3750000, 3750000, 3750000, 3749999])
            self.assertEqual(r['producer_backlog_limit'], 256)

    def test_hardware_all_six_raw_bound_and_macros(self):
        self.assertEqual(len(self.d['hardware']), 6)
        self.assertEqual([r['area'] for r in self.d['hardware']],
            ['106163.066946', '212027.006396', '423513.448454', '109794.784709', '218863.734160', '436771.124393'])
        for r in self.d['hardware']:
            self.assertGreater(float(r['setup_slack_ns']), 0)
            self.assertGreaterEqual(r['untested_checks'], 0)
            for name in ('area.rpt', 'area_summary.rpt', 'pt_timing_max.rpt', 'pt_timing_min.rpt', 'profile_applied.rpt'):
                self.assertIn(r['report_root']+'/'+name, self.d['inputs'])
        self.assertEqual([r['untested_checks'] for r in self.d['hardware']], [68, 64, 0, 68, 4, 0])
        for name in ('ImprovementCgofHardwareTable', 'ImprovementFiniteHeavyModelTable',
                     'ImprovementProductionRtlTable', 'ImprovementFixedClassTable'):
            self.assertEqual(self.tex.count('\\newcommand{\\'+name+'}'), 1)
        self.assertEqual(self.d['output_tex_sha256'], g.digest(self.tex.encode()))

    def test_nearest_rank_and_changed_handoff_rejected(self):
        self.assertEqual(g.histogram_p99({'0': 99, '100': 1}), 0)
        self.assertEqual(g.histogram_p99({'0': 98, '100': 2}), 100)
        for hist in ({}, {'0': -1}, {'-1': 4}):
            with self.assertRaises(ValueError): g.histogram_p99(hist)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root/g.IMPROVEMENT_HANDOFF
            p.parent.mkdir(parents=True)
            p.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                g.improvement_data(root)


if __name__=='__main__':unittest.main()
