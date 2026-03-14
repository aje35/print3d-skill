"""Integration tests for the knowledge system (US3).

Tests query filtering with AND logic, wildcards, and schema validation.
"""

from __future__ import annotations

from print3d_skill import query_knowledge


class TestModeQuery:
    def test_create_mode_returns_matching_files(self):
        results = query_knowledge(mode="create")
        assert len(results) > 0
        for kf in results:
            # File must either list "create" in modes or have empty modes (all)
            assert (
                "create" in kf.metadata.modes or len(kf.metadata.modes) == 0
            )

    def test_fix_mode_returns_matching_files(self):
        results = query_knowledge(mode="fix")
        assert len(results) > 0
        for kf in results:
            assert "fix" in kf.metadata.modes or len(kf.metadata.modes) == 0


class TestMaterialQuery:
    def test_pla_material_returns_matching_files(self):
        results = query_knowledge(material="PLA")
        assert len(results) > 0
        for kf in results:
            assert (
                "PLA" in kf.metadata.materials or len(kf.metadata.materials) == 0
            )


class TestANDQuery:
    def test_mode_and_material_combined(self):
        results = query_knowledge(mode="create", material="PLA")
        assert len(results) > 0
        for kf in results:
            mode_ok = "create" in kf.metadata.modes or len(kf.metadata.modes) == 0
            mat_ok = "PLA" in kf.metadata.materials or len(kf.metadata.materials) == 0
            assert mode_ok and mat_ok

    def test_narrow_query_reduces_results(self):
        broad = query_knowledge(mode="create")
        narrow = query_knowledge(mode="create", material="ABS")
        # Narrow should have fewer or equal results
        assert len(narrow) <= len(broad)


class TestWildcardBehavior:
    def test_no_filters_returns_all_files(self):
        results = query_knowledge()
        # Should return all 4 seed files
        assert len(results) >= 4

    def test_none_fields_are_wildcards(self):
        all_results = query_knowledge()
        mode_results = query_knowledge(mode="create")
        # Wildcard should return at least as many as filtered
        assert len(all_results) >= len(mode_results)


class TestEmptyResults:
    def test_no_match_returns_empty_list(self):
        # Files with empty modes match any mode (wildcard behavior).
        # To get a true empty result, combine filters that no file satisfies.
        results = query_knowledge(mode="nonexistent_mode", material="UNOBTAINIUM")
        assert results == []

    def test_wildcard_files_still_match_unknown_values(self):
        # Files with modes=[] match ANY mode query (they apply to all modes)
        results = query_knowledge(mode="nonexistent_mode")
        assert isinstance(results, list)
        # seed_material_properties has modes=[] so it matches
        for kf in results:
            assert len(kf.metadata.modes) == 0


class TestKnowledgeFileContent:
    def test_files_have_data(self):
        results = query_knowledge()
        for kf in results:
            assert kf.data is not None
            assert isinstance(kf.data, dict)

    def test_files_have_metadata(self):
        results = query_knowledge()
        for kf in results:
            assert kf.metadata.type
            assert kf.metadata.topic

    def test_tolerance_table_has_entries(self):
        results = query_knowledge(problem_type="tolerance_table")
        assert len(results) >= 1
        for kf in results:
            assert "entries" in kf.data or "description" in kf.data
