from copy import deepcopy
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase, override_settings

from .advisor.assembly import assemble
from .advisor.catalog import available
from .advisor.fields import ProductVectorField
from .advisor.pipeline import respond
from .advisor.requirements import clarify, drop_unmentioned, merge_sheet
from .advisor.rules import blocked, check_build
from .chat_service import ChatUnavailable


def fixture():
    specs = {
        'cpu': {'socket': 'AM5', 'tdp_w': 65, 'has_igpu': True, 'stock_cooler': True},
        'mainboard': {'socket': 'AM5', 'ram_type': 'DDR5', 'ram_slots': 4,
                      'max_ram_gb': 128, 'm2_slots': 2, 'form_factor': 'ATX'},
        'ram': {'ram_type': 'DDR5', 'modules': 2, 'capacity_gb': 32},
        'gpu': {'tdp_w': 200, 'length_mm': 280},
        'cooler': {'sockets': ['AM5'], 'tdp_w': 150, 'height_mm': 150, 'cooler_type': 'air'},
        'ssd': {'interface': 'nvme'},
        'psu': {'watt': 650},
        'case': {'supported_mb': ['ATX'], 'max_gpu_length_mm': 320, 'max_cooler_height_mm': 160},
    }
    return [{'id': cat, 'cat': cat, 'name': cat, 'price': 100000, 'stock': 3,
             'specs': data, 'brand': 'amd' if cat == 'cpu' else 'test'} for cat, data in specs.items()]


SHEET = {'ngan_sach': 25000000, 'muc_dich': 'gaming', 'hang_cpu': 'tuy_shop',
         'gom_man_hinh_phim_chuot': False, 'gom_ban_quyen': False}


class AdvisorRuleTests(SimpleTestCase):
    def test_complete_compatible_configuration(self):
        checks = check_build(fixture())
        self.assertEqual({c['code'] for c in checks}, {f'R{i}' for i in range(1, 15)})
        self.assertTrue(all(c['status'] == 'pass' for c in checks))
        self.assertFalse(blocked(checks))

    def test_every_hardware_rule_detects_conflict(self):
        cases = [
            ('R1', 'cpu', 'socket', 'AM4'),
            ('R2', 'ram', 'ram_type', 'DDR4'),
            ('R3', 'ram', 'modules', 5),
            ('R4', 'ram', 'capacity_gb', 256),
            ('R5', 'mainboard', 'm2_slots', 0),
            ('R6', 'cooler', 'sockets', ['LGA1700']),
            ('R7', 'cooler', 'tdp_w', 20),
            ('R8', 'psu', 'watt', 400),
            ('R9', 'case', 'supported_mb', ['Mini-ITX']),
            ('R10', 'gpu', 'length_mm', 400),
            ('R11', 'cooler', 'height_mm', 200),
        ]
        for code, cat, key, value in cases:
            with self.subTest(code=code):
                products = fixture()
                next(p for p in products if p['cat'] == cat)['specs'][key] = value
                check = next(c for c in check_build(products) if c['code'] == code)
                self.assertEqual(check['status'], 'fail')

    def test_psu_formula_exact_boundary(self):
        products = fixture()
        psu = next(p for p in products if p['cat'] == 'psu')
        psu['specs']['watt'] = 442
        self.assertEqual(next(c for c in check_build(products) if c['code'] == 'R8')['status'], 'pass')
        psu['specs']['watt'] = 441
        self.assertEqual(next(c for c in check_build(products) if c['code'] == 'R8')['status'], 'fail')

    def test_missing_gpu_cooler_and_components(self):
        products = [p for p in fixture() if p['cat'] not in ('gpu', 'cooler', 'ssd')]
        cpu = next(p for p in products if p['cat'] == 'cpu')
        cpu['specs'].update(has_igpu=False, stock_cooler=False)
        checks = {c['code']: c for c in check_build(products)}
        for code in ('R12', 'R13', 'R14'):
            self.assertEqual(checks[code]['status'], 'fail')
        self.assertEqual(checks['R14']['severity'], 'warning')

    def test_unknown_cannot_be_certified(self):
        products = fixture()
        products[0]['specs'].pop('socket')
        checks = check_build(products)
        self.assertTrue(blocked(checks))
        self.assertEqual(next(c for c in checks if c['code'] == 'R1')['status'], 'unknown')

    def test_secondary_unknown_is_warning_but_core_unknown_blocks(self):
        products = fixture()
        for cat, key in (('gpu', 'length_mm'), ('mainboard', 'max_ram_gb'), ('mainboard', 'm2_slots')):
            next(p for p in products if p['cat'] == cat)['specs'].pop(key)
        cpu = next(p for p in products if p['cat'] == 'cpu')
        cpu['specs'].pop('has_igpu')  # đã có VGA rời: R12 đạt
        checks = {c['code']: c for c in check_build(products)}
        for code in ('R4', 'R5', 'R10'):
            self.assertEqual((checks[code]['status'], checks[code]['severity']), ('unknown', 'warning'))
        self.assertEqual(checks['R12']['status'], 'pass')
        self.assertFalse(blocked(checks.values()))
        next(p for p in products if p['cat'] == 'gpu')['specs']['length_mm'] = 400  # vượt 320mm của case
        self.assertTrue(blocked(check_build(products)))

    def test_partial_does_not_require_gpu_or_complete_build(self):
        checks = check_build(fixture()[:1], final=False)
        self.assertFalse(blocked(checks))
        self.assertNotIn('R13', {c['code'] for c in checks})


class RequirementTests(SimpleTestCase):
    def test_merge_only_explicit_updates(self):
        self.assertEqual(merge_sheet({'ngan_sach': 100}, {'ngan_sach': None, 'muc_dich': 'gaming'})['ngan_sach'], 100)
        for bad in ({'ngan_sach': True}, {'ngan_sach': -1}, {'muc_dich': 'other'}, {'gom_ban_quyen': 'no'}):
            with self.assertRaises(ChatUnavailable):
                merge_sheet({}, bad)

    def test_only_core_needs_are_asked_then_defaults_are_assumed(self):
        sheet, counts, questions, assumptions = clarify({}, {})
        self.assertEqual(len(questions), 2)
        self.assertIsNone(sheet.get('ngan_sach'))
        self.assertEqual(assumptions, [])
        # Đủ ngân sách + mục đích: tư vấn ngay, không hỏi thêm màn hình/Windows mà ghi rõ giả định.
        sheet, counts, questions, assumptions = clarify({'ngan_sach': 100, 'muc_dich': 'gaming'}, counts)
        self.assertEqual(questions, [])
        self.assertFalse(sheet['gom_ban_quyen'])
        self.assertFalse(sheet['gom_man_hinh_phim_chuot'])
        self.assertEqual(len(assumptions), 2)
        sheet, _, _, assumptions = clarify({'ngan_sach': 100, 'muc_dich': 'gaming', 'gom_ban_quyen': True}, {})
        self.assertTrue(sheet['gom_ban_quyen'])
        self.assertEqual(assumptions, ['Ngân sách chưa gồm màn hình, bàn phím, chuột.'])

    def test_optional_fields_need_explicit_mention(self):
        extracted = {'ngan_sach': 40000000, 'muc_dich': 'gaming', 'gom_man_hinh_phim_chuot': True, 'gom_ban_quyen': True}
        self.assertEqual(drop_unmentioned(extracted, 'cấu hình 40 triệu cho gaming'),
                         {**extracted, 'gom_man_hinh_phim_chuot': None, 'gom_ban_quyen': None})
        kept = drop_unmentioned(extracted, '40tr chơi game, đã gồm màn hình và Win 11 bản quyền')
        self.assertTrue(kept['gom_man_hinh_phim_chuot'] and kept['gom_ban_quyen'])

    @override_settings(ADVISOR_HYDE=True)
    @patch('core.advisor.pipeline.hybrid_search')
    def test_no_hyde_or_retrieval_before_requirements_complete(self, retrieval):
        def generate(*args, **kwargs):
            return {'ngan_sach': 25000000}
        result, state = respond('25tr', [], fixture(), [], {}, generate)
        self.assertEqual(result['stage'], 'clarification')
        retrieval.assert_not_called()
        self.assertEqual(state['sheet']['ngan_sach'], 25000000)
        self.assertEqual(result['quick_replies'][0]['question'], result['questions'][0])
        self.assertIn('Chơi game', result['quick_replies'][0]['options'])


class AssemblyTests(SimpleTestCase):
    def test_budget_stock_and_compatibility(self):
        result = assemble(SHEET, fixture())
        self.assertTrue(result['can_add_to_cart'])
        self.assertLessEqual(result['total'], SHEET['ngan_sach'])
        self.assertFalse(blocked(result['checks']))

    def test_office_uses_integrated_graphics(self):
        catalog = fixture()
        next(p for p in catalog if p['cat'] == 'cpu')['specs']['has_igpu'] = False
        result = assemble({**SHEET, 'muc_dich': 'van_phong'}, catalog)
        self.assertFalse(result['can_add_to_cart'])
        self.assertNotIn('gpu', {p['cat'] for p in result['products']})

    def test_unknown_stock_is_excluded(self):
        for stock in (None, 0, -1, True, 'unknown'):
            self.assertFalse(available({'stock': stock, 'price': 100}))

    def test_license_and_peripheral_reservations(self):
        catalog = fixture() + [{'id': 'license', 'cat': 'license', 'price': 1000000, 'stock': 1, 'specs': {}}]
        result = assemble({**SHEET, 'gom_man_hinh_phim_chuot': True, 'gom_ban_quyen': True}, catalog)
        self.assertEqual(result['peripheral_reserve'], 5000000)
        self.assertEqual(result['component_budget'], 19000000)
        self.assertIn('license', {p['id'] for p in result['products']})

    def test_missing_license_blocks_and_impossible_budget_proposes_cheapest_complete(self):
        self.assertFalse(assemble({**SHEET, 'gom_ban_quyen': True}, fixture())['can_add_to_cart'])
        result = assemble({**SHEET, 'ngan_sach': 1}, fixture())
        self.assertEqual(result['proposal'], 'cheapest_complete')
        self.assertEqual({p['cat'] for p in result['products']}, {'cpu', 'mainboard', 'ram', 'gpu', 'ssd', 'psu', 'case'})
        self.assertEqual(result['over_budget'], result['total'] - 1)
        self.assertFalse(blocked(result['checks']))

    def test_group_over_ratio_is_completed_when_total_fits(self):
        catalog = fixture()
        next(p for p in catalog if p['cat'] == 'ram')['price'] = 5000000  # hạn mức RAM 8% = 2 triệu
        result = assemble(SHEET, catalog)
        self.assertIn('ram', {p['cat'] for p in result['products']})
        self.assertTrue(result['can_add_to_cart'])
        self.assertIsNone(result['alternatives'])

    def test_gaming_skips_workstation_gpu_oversized_psu_and_orphan_cpu(self):
        def item(id, cat, price, name, **specs):
            return {'id': id, 'cat': cat, 'name': name, 'price': price, 'stock': 1, 'brand': 'amd', 'specs': specs}
        catalog = fixture() + [
            item('gpu-pro', 'gpu', 3000000, 'NVIDIA RTX A4000 16GB', tdp_w=140, length_mm=240),
            item('gpu-710', 'gpu', 50000, 'GeForce 710 2GB', tdp_w=19, length_mm=150),
            item('psu-1600', 'psu', 5000000, 'PSU 1600W', watt=1600),
            item('cpu-am4', 'cpu', 4000000, 'Ryzen AM4', socket='AM4', tdp_w=65, has_igpu=False, stock_cooler=True),
        ]
        ids = {p['cat']: p['id'] for p in assemble(SHEET, catalog)['products']}
        self.assertEqual((ids['gpu'], ids['psu'], ids['cpu']), ('gpu', 'psu', 'cpu'))

    def test_leftover_budget_upgrades_gpu(self):
        catalog = fixture() + [{'id': 'gpu-big', 'cat': 'gpu', 'name': 'RTX lớn', 'price': 12000000, 'stock': 1,
                                'brand': 'test', 'specs': {'tdp_w': 200, 'length_mm': 300}}]
        result = assemble({**SHEET, 'ngan_sach': 15000000}, catalog)  # hạn mức GPU 35% = 5,25 triệu
        self.assertIn('gpu-big', {p['id'] for p in result['products']})
        self.assertTrue(result['can_add_to_cart'])

    def test_over_budget_proposes_lowest_total_not_greedy_cheapest_parts(self):
        catalog = fixture() + [
            # VGA rẻ hơn nhưng ngốn điện: cần nguồn >= (65+400+75)*1,3 = 702W, chỉ có nguồn 1000W giá 3 triệu.
            {'id': 'gpu-hungry', 'cat': 'gpu', 'name': 'GPU hungry', 'price': 50000, 'stock': 1, 'brand': 'test',
             'specs': {'tdp_w': 400, 'length_mm': 280}},
            {'id': 'psu-big', 'cat': 'psu', 'name': 'PSU 1000W', 'price': 3000000, 'stock': 1, 'brand': 'test',
             'specs': {'watt': 1000}},
        ]
        result = assemble({**SHEET, 'ngan_sach': 1}, catalog)
        ids = {p['cat']: p['id'] for p in result['products']}
        self.assertEqual((ids['gpu'], ids['psu']), ('gpu', 'psu'))
        self.assertEqual(result['total'], 7 * 100000)
        self.assertEqual(result['over_budget'], 7 * 100000 - 1)

    def test_cheapest_complete_within_budget_is_upgraded_not_flagged(self):
        catalog = fixture()
        next(p for p in catalog if p['cat'] == 'ram')['price'] = 9000000  # vượt hạn mức RAM nhưng tổng vẫn vừa
        catalog.append({'id': 'gpu-big', 'cat': 'gpu', 'name': 'GPU lớn', 'price': 10000000, 'stock': 1,
                        'brand': 'test', 'specs': {'tdp_w': 200, 'length_mm': 300}})
        result = assemble({**SHEET, 'ngan_sach': 20000000}, catalog)
        self.assertEqual((result['proposal'], result['over_budget']), ('budget', 0))
        self.assertLessEqual(result['total'], 20000000)
        self.assertTrue(result['can_add_to_cart'])

    def test_complete_build_has_no_alternatives(self):
        self.assertIsNone(assemble(SHEET, fixture())['alternatives'])

    def test_missing_group_reports_cheapest_fit_and_budget_shortfall(self):
        catalog = fixture()
        next(p for p in catalog if p['cat'] == 'mainboard')['price'] = 20000000
        result = assemble({**SHEET, 'ngan_sach': 10000000}, catalog)
        self.assertEqual((result['proposal'], result['over_budget']), ('cheapest_complete', 20000000 + 6 * 100000 - 10000000))
        self.assertIn('mainboard', {p['cat'] for p in result['products']})
        alt = result['alternatives']
        entry = next(m for m in alt['missing'] if m['cat'] == 'mainboard')
        self.assertEqual((entry['reason'], entry['product']['id']), ('over_allowance', 'mainboard'))
        self.assertEqual(entry['over_by'], 20000000 - result['allocations']['mainboard'])
        self.assertEqual(alt['min_build_total'], 20000000 + 6 * 100000)
        self.assertEqual(alt['budget_shortfall'], alt['min_build_total'] - 10000000)

    def test_other_brand_cpu_is_offered_when_preferred_brand_missing(self):
        result = assemble({**SHEET, 'hang_cpu': 'intel'}, fixture())
        alt = result['alternatives']
        entry = next(m for m in alt['missing'] if m['cat'] == 'cpu')
        self.assertEqual(entry['reason'], 'no_compatible_product')
        self.assertEqual(entry['other_brand']['id'], 'cpu')
        self.assertTrue(alt['brand_unavailable'])
        self.assertEqual(alt['budget_shortfall'], 0)

    def test_pinned_product_cannot_silently_disappear(self):
        self.assertFalse(assemble(SHEET, fixture(), selected_ids=['not-real'])['can_add_to_cart'])

    def test_pinned_product_above_category_ratio_is_kept_when_total_budget_allows(self):
        catalog = fixture()
        pinned_cpu = deepcopy(next(p for p in catalog if p['cat'] == 'cpu'))
        pinned_cpu.update(id='cpu-pro', price=7000000)
        result = assemble(SHEET, catalog + [pinned_cpu], selected_ids=['cpu-pro'])
        self.assertTrue(result['can_add_to_cart'])
        self.assertIn('cpu-pro', {p['id'] for p in result['products']})

    def test_aio_cooler_does_not_block_case_selection(self):
        catalog = fixture()
        aio = deepcopy(next(p for p in catalog if p['cat'] == 'cooler'))
        aio.update(id='aio-cooler', price=200000)
        aio['specs']['cooler_type'] = 'aio'
        result = assemble(SHEET, catalog + [aio], ranked_ids=['aio-cooler'])
        self.assertTrue(result['can_add_to_cart'])
        self.assertIn('aio-cooler', {p['id'] for p in result['products']})
        self.assertIn('case', {p['cat'] for p in result['products']})
        r11 = next(c for c in result['checks'] if c['code'] == 'R11')
        self.assertEqual((r11['severity'], r11['status']), ('warning', 'unknown'))

    def test_air_cooler_without_height_still_blocks(self):
        products = fixture()
        next(p for p in products if p['cat'] == 'cooler')['specs'].pop('height_mm')
        checks = check_build(products)
        self.assertEqual(next(c for c in checks if c['code'] == 'R11')['status'], 'unknown')
        self.assertTrue(blocked(checks))

    def test_incompatible_candidate_is_replaced(self):
        catalog = fixture()
        bad = deepcopy(next(p for p in catalog if p['cat'] == 'mainboard'))
        bad.update(id='bad', price=200000)
        bad['specs']['socket'] = 'AM4'
        result = assemble(SHEET, catalog + [bad], ranked_ids=['bad'])
        self.assertNotIn('bad', {p['id'] for p in result['products']})
        self.assertTrue(result['can_add_to_cart'])

    def test_retrieval_receives_only_candidates_within_each_allowance(self):
        calls = []
        def retrieve(candidates):
            calls.append(candidates)
            return [p['id'] for p in candidates]
        result = assemble(SHEET, fixture(), retrieve=retrieve)
        for candidates in calls:
            self.assertEqual(len({p['cat'] for p in candidates}), 1)
            self.assertTrue(all(p['price'] <= result['allocations'][p['cat']] for p in candidates))

    def test_retrieved_first_then_highest_price(self):
        catalog = fixture()
        base = next(p for p in catalog if p['cat'] == 'ssd')
        cheap, pricey = deepcopy(base), deepcopy(base)
        cheap.update(id='ssd-retrieved', price=base['price'] + 1000)
        pricey.update(id='ssd-pricey', price=base['price'] + 2000)
        def retrieve(candidates):
            ids = [p['id'] for p in candidates]
            return ['ssd-retrieved'] if 'ssd-retrieved' in ids else []
        ids = {p['id'] for p in assemble(SHEET, catalog + [cheap, pricey], retrieve=retrieve)['products']}
        self.assertIn('ssd-retrieved', ids)
        ids = {p['id'] for p in assemble(SHEET, catalog + [cheap, pricey])['products']}
        self.assertIn('ssd-pricey', ids)

    def test_vector_validation(self):
        from django.core.exceptions import ValidationError
        field = ProductVectorField()
        for vector in ([1.0], [float('nan')] * 1024):
            with self.assertRaises(ValidationError):
                field.get_prep_value(vector)


class ExperimentTests(SimpleTestCase):
    def test_llm_selector_is_rechecked_by_rules(self):
        from .advisor.llm_select import llm_assemble
        catalog = fixture()
        bad = deepcopy(next(p for p in catalog if p['cat'] == 'mainboard'))
        bad.update(id='bad-board')
        bad['specs']['socket'] = 'LGA1700'
        ids = ['cpu', 'bad-board', 'ram', 'gpu', 'cooler', 'ssd', 'psu', 'case', 'invented']
        result = llm_assemble(SHEET, catalog + [bad], None, lambda *a, **kw: {'product_ids': ids})
        self.assertEqual(result['invalid_ids'], ['invented'])
        self.assertEqual(next(c for c in result['checks'] if c['code'] == 'R1')['status'], 'fail')
        self.assertFalse(result['can_add_to_cart'])

    @override_settings(ADVISOR_HYDE=False, ADVISOR_RETRIEVAL='lexical')
    def test_pipeline_routes_to_llm_selector(self):
        calls = iter([dict(SHEET), {'product_ids': [p['id'] for p in fixture()]}, 'Cấu hình.'])
        result, _ = respond('PC gaming', [], fixture(), [], {}, lambda *a, **kw: next(calls), selector='llm')
        self.assertEqual(result['selector'], 'llm')
        self.assertTrue(result['can_add_to_cart'])

    def test_budget_within_five_percent(self):
        from .management.commands.evaluate_advisor import budget_metrics
        sheet = {'ngan_sach': 100}
        rec = {'stage': 'recommendation', 'peripheral_reserve': 0}
        self.assertEqual(budget_metrics({**rec, 'total': 96}, sheet), (True, True))
        self.assertEqual(budget_metrics({**rec, 'total': 104}, sheet), (True, False))
        self.assertEqual(budget_metrics({**rec, 'total': 90}, sheet), (False, True))
        self.assertEqual(budget_metrics({**rec, 'total': 76, 'peripheral_reserve': 20}, sheet), (True, True))
        self.assertEqual(budget_metrics({'stage': 'clarification'}, sheet), (None, None))

    @patch('core.advisor.retrieval.embed')
    def test_hyde_modes_and_memory_store_accept_other_dimensions(self, embed):
        from .advisor import retrieval
        embed.side_effect = lambda texts: [[1.0, 0.0, 0.0] if 'q' in t else [0.0, 1.0, 0.0] for t in texts]
        retrieval.query_vectors.cache_clear()
        with override_settings(ADVISOR_HYDE_MODE='only'):
            self.assertEqual(retrieval.combined_vector('q', 'h'), [0.0, 1.0, 0.0])
        retrieval.query_vectors.cache_clear()
        with override_settings(ADVISOR_HYDE_MODE='combined'):
            self.assertAlmostEqual(retrieval.combined_vector('q', 'h')[0], 2 ** -0.5)
        retrieval._memory_index.clear()
        catalog = [{'id': 'a', 'name': 'q match'}, {'id': 'b', 'name': 'other'}]
        with override_settings(ADVISOR_VECTOR_STORE='memory', ADVISOR_EMBEDDING_MODEL='mini'):
            self.assertEqual(retrieval.memory_semantic([1.0, 0.0, 0.0], catalog), ['a', 'b'])


class PipelineIntegrationTests(SimpleTestCase):
    @override_settings(ADVISOR_HYDE=False)
    @patch('core.advisor.pipeline.hybrid_search')
    def test_lookup_with_known_core_needs(self, retrieval):
        retrieval.return_value = (['cpu'], {'mode': 'test', 'retrieved_ids': ['cpu']})
        calls = iter([{'intent': 'lookup'}, 'CPU còn hàng.'])
        result, state = respond('Giá CPU?', [], fixture(), [], {'sheet': dict(SHEET), 'recommended': True},
                                lambda *a, **kw: next(calls))
        self.assertEqual(result['stage'], 'lookup')
        self.assertFalse(result['can_add_to_cart'])
        self.assertEqual(result['products'][0]['id'], 'cpu')
        self.assertNotIn('ask_counts', state)

    @override_settings(ADVISOR_HYDE=False)
    @patch('core.advisor.pipeline.assemble')
    @patch('core.advisor.pipeline.hybrid_search')
    def test_first_consultation_builds_even_if_llm_says_lookup(self, retrieval, assemble_mock):
        assemble_mock.return_value = {'products': [], 'checks': [], 'can_add_to_cart': True}
        retrieval.return_value = ([], {'mode': 'test', 'retrieved_ids': []})
        for state, extracted in (({}, {**SHEET, 'intent': 'lookup'}),
                                 ({'sheet': dict(SHEET), 'recommended': True}, {'ngan_sach': 30000000, 'intent': 'lookup'})):
            with self.subTest(state=state):
                calls = iter([extracted, 'Cấu hình.'])
                result, next_state = respond('máy 20 triệu chơi game', [], fixture(), [], state, lambda *a, **kw: next(calls))
                self.assertEqual(result['stage'], 'recommendation')
                self.assertTrue(next_state['recommended'])

    @override_settings(ADVISOR_HYDE=False)
    @patch('core.advisor.pipeline.hybrid_search')
    def test_over_budget_answer_always_starts_with_backend_warning(self, retrieval):
        retrieval.return_value = ([], {'mode': 'test', 'retrieved_ids': []})
        narrative = ('- CPU: phù hợp chơi game.\n'
                     'Tổng vượt ngân sách. Anh/chị có thể thay thế RAM bằng loại rẻ hơn. Có thể bỏ Windows để giảm chi phí.')
        calls = iter([{**SHEET, 'ngan_sach': 500000, 'intent': 'build'}, narrative])
        result, _ = respond('máy 500 nghìn chơi game', [], fixture(), [], {}, lambda *a, **kw: next(calls))
        self.assertEqual(result['proposal'], 'cheapest_complete')
        answer = result['answer']
        self.assertTrue(answer.startswith('⚠️ Cảnh báo: với hàng đang có, ngân sách 500.000 ₫ chưa đủ'))
        self.assertIn('vượt ngân sách 200.000 ₫', answer)
        self.assertIn('- CPU: phù hợp chơi game.', answer)
        self.assertNotIn('thay thế RAM', answer)  # đã là bộ rẻ nhất: không gợi ý đổi linh kiện rẻ hơn
        self.assertIn('Có thể bỏ Windows để giảm chi phí.', answer)
        self.assertTrue(answer.endswith('Anh/chị có đồng ý tăng ngân sách để mua cấu hình này không ạ?'))

    @override_settings(ADVISOR_HYDE=False)
    @patch('core.advisor.pipeline.hybrid_search')
    def test_swap_rebuilds_with_pinned_product_even_if_llm_says_lookup(self, retrieval):
        retrieval.return_value = ([], {'mode': 'test', 'retrieved_ids': []})
        catalog = fixture() + [{'id': 'ram-2', 'cat': 'ram', 'name': 'ram 2', 'price': 90000, 'stock': 2,
                                'brand': 'test', 'specs': {'ram_type': 'DDR5', 'modules': 2, 'capacity_gb': 16}}]
        calls = iter([{'intent': 'lookup'}, 'Đã đổi RAM.'])
        result, _ = respond('Đổi RAM sang ram 2', [], catalog, ['ram-2'], {'sheet': dict(SHEET)},
                            lambda *a, **kw: next(calls), swap=True)
        self.assertEqual(result['stage'], 'recommendation')
        ram = next(p for p in result['products'] if p['cat'] == 'ram')
        self.assertEqual(ram['id'], 'ram-2')
        self.assertFalse(blocked(result['checks']))

    @override_settings(ADVISOR_HYDE=True)
    @patch('core.advisor.pipeline.hybrid_search')
    def test_missing_core_needs_block_all_search_even_lookup_intent(self, retrieval):
        from unittest.mock import Mock
        for sheet, expected_questions in (({}, 2), ({'ngan_sach': 20000000}, 1),
                                           ({'muc_dich': 'gaming'}, 1)):
            with self.subTest(sheet=sheet):
                generate = Mock(return_value={'intent': 'lookup'})
                result, state = respond('Tôi cần mua máy tính', [], fixture(), [],
                                        {'sheet': sheet}, generate)
                self.assertEqual(result['stage'], 'clarification')
                self.assertTrue(result['answer'].startswith('Em chưa thể tư vấn cấu hình vì anh/chị chưa cung cấp đủ thông tin'))
                self.assertEqual(len(result['questions']), expected_questions)
                self.assertEqual(len(result['missing_info']), expected_questions)
                self.assertEqual(result['products'], [])
                self.assertFalse(result['can_add_to_cart'])
                generate.assert_called_once()
                retrieval.assert_not_called()
                for key, value in sheet.items():
                    self.assertEqual(state['sheet'][key], value)

    @override_settings(ADVISOR_HYDE=False, ADVISOR_RETRIEVAL='lexical')
    def test_complete_turn_selects_products_without_llm_ids(self):
        calls = iter([dict(SHEET), 'Cấu hình theo ngân sách.'])
        result, state = respond('PC gaming', [], fixture(), [], {}, lambda *a, **kw: next(calls))
        self.assertEqual(result['stage'], 'recommendation')
        self.assertTrue(result['can_add_to_cart'])
        self.assertEqual(result['requirements']['ngan_sach'], 25000000)
        self.assertEqual(len(result['products']), 8)
        self.assertGreaterEqual(result['latency_ms'], 0)
