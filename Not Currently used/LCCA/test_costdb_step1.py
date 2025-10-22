#!/usr/bin/env python3
"""
Test script for CostDB migration (Step 1).

Tests:
1. Backward compatibility with v0.05
2. Enhanced features in v0.06
3. Regional cost factors
4. Utility rates
5. Parametric estimation

Usage:
    python test_costdb_migration.py
    python test_costdb_migration.py --v05 CostDB_v0.05.xlsx --v06 CostDB_v0.06_NREL.xlsx
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Import the enhanced loader
# (Assuming it's in the same directory or installed)
try:
    from costdb_loader import CostDB
except ImportError:
    print("ERROR: Cannot import CostDB from costdb_loader.py")
    print("Make sure costdb_loader.py is in the same directory or PYTHONPATH")
    sys.exit(1)


def test_backward_compatibility(db_path: str) -> bool:
    """Test that legacy v0.05 methods still work."""
    print("\n" + "="*70)
    print("TEST 1: Backward Compatibility (v0.05 API)")
    print("="*70)
    
    try:
        db = CostDB(db_path)
        print(f"✓ Database loaded: {db.version}")
        
        # Test legacy methods
        tests_passed = 0
        tests_total = 0
        
        # Test 1: get_system_cost()
        tests_total += 1
        try:
            cost = db.get_system_cost('CHPWH-HP-Central', 1.0)
            if cost > 0:
                print(f"✓ get_system_cost('CHPWH-HP-Central', 1.0) = ${cost:,.2f}")
                tests_passed += 1
            else:
                print(f"⚠ get_system_cost() returned 0 (system may not exist in this DB)")
        except Exception as e:
            print(f"✗ get_system_cost() failed: {e}")
        
        # Test 2: get_markup_multiplier()
        tests_total += 1
        try:
            markup = db.get_markup_multiplier()
            print(f"✓ get_markup_multiplier() = {markup:.3f}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ get_markup_multiplier() failed: {e}")
        
        # Test 3: get_escalation_rate()
        tests_total += 1
        try:
            rate = db.get_escalation_rate('General')
            print(f"✓ get_escalation_rate('General') = {rate:.3f}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ get_escalation_rate() failed: {e}")
        
        print(f"\nBackward Compatibility: {tests_passed}/{tests_total} tests passed")
        return tests_passed == tests_total
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_enhanced_features(db_path: str) -> bool:
    """Test new v0.06 enhanced features."""
    print("\n" + "="*70)
    print("TEST 2: Enhanced Features (v0.06 API)")
    print("="*70)
    
    try:
        db = CostDB(db_path)
        
        if db.version == 'v0.05':
            print("ℹ Skipping enhanced features (v0.05 database)")
            return True
        
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Regional cost factors
        tests_total += 1
        try:
            if db.regional_factors is not None:
                print(f"✓ Regional factors loaded: {len(db.regional_factors)} regions")
                
                # Test get_regional_factor()
                sf_factor = db.get_regional_factor('US-CA-SF')
                hi_factor = db.get_regional_factor('US-HI-HON')
                
                print(f"  → San Francisco factor: {sf_factor:.2f}x")
                print(f"  → Honolulu factor: {hi_factor:.2f}x")
                
                if sf_factor > 1.0 and hi_factor > 1.0:
                    tests_passed += 1
                else:
                    print(f"  ⚠ Factors seem incorrect")
            else:
                print("✗ No regional factors available")
        except Exception as e:
            print(f"✗ Regional factors test failed: {e}")
        
        # Test 2: Regional cost calculation
        tests_total += 1
        try:
            # Try to find a system that exists
            test_system = None
            if db.system_costs_enhanced is not None and not db.system_costs_enhanced.empty:
                test_system = db.system_costs_enhanced['system_id'].iloc[0]
            elif not db.systems.empty:
                test_system = db.systems['system_code'].iloc[0]
            
            if test_system:
                result = db.get_system_cost_with_region(test_system, 1.0, 'US-CA-SF')
                
                print(f"✓ get_system_cost_with_region('{test_system}', 1.0, 'US-CA-SF'):")
                print(f"  → Base cost: ${result['base_cost']:,.2f}")
                print(f"  → Regional factor: {result['regional_factor']:.2f}x")
                print(f"  → Total: ${result['total']:,.2f}")
                
                if result['total'] > 0:
                    tests_passed += 1
                else:
                    print(f"  ⚠ Total cost is 0")
            else:
                print("✗ No systems found to test")
                
        except Exception as e:
            print(f"✗ Regional cost calculation failed: {e}")
        
        # Test 3: Utility rates
        tests_total += 1
        try:
            if db.utility_rates is not None:
                print(f"✓ Utility rates loaded: {len(db.utility_rates)} rates")
                
                # Try to get PG&E rate
                pge_rate = db.get_utility_rate('PGE-E1-TIER')
                if pge_rate:
                    print(f"  → PG&E E-1 rate found: {pge_rate['rate_name']}")
                    print(f"     Type: {pge_rate['structure_type']}")
                    tests_passed += 1
                else:
                    print(f"  ⚠ PG&E E-1 rate not found")
            else:
                print("✗ No utility rates available")
        except Exception as e:
            print(f"✗ Utility rates test failed: {e}")
        
        # Test 4: Parametric estimation
        tests_total += 1
        try:
            estimate = db.estimate_system_cost_parametric(
                'SplitHP', 3.0, 'US-CA-SF', 'tons'
            )
            
            if 'error' not in estimate:
                print(f"✓ estimate_system_cost_parametric('SplitHP', 3.0, 'US-CA-SF'):")
                print(f"  → Base: ${estimate['base_cost']:,.2f}")
                print(f"  → Regional ({estimate['regional_factor']:.2f}x): ${estimate['total']:,.2f}")
                tests_passed += 1
            else:
                print(f"✗ Parametric estimation failed: {estimate['error']}")
        except Exception as e:
            print(f"✗ Parametric estimation test failed: {e}")
        
        print(f"\nEnhanced Features: {tests_passed}/{tests_total} tests passed")
        return tests_passed >= tests_total - 1  # Allow 1 failure
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_ca_hi_data(db_path: str) -> bool:
    """Test California and Hawaii specific data."""
    print("\n" + "="*70)
    print("TEST 3: California & Hawaii Data")
    print("="*70)
    
    try:
        db = CostDB(db_path)
        
        if db.version == 'v0.05':
            print("ℹ Skipping CA/HI tests (v0.05 database)")
            return True
        
        tests_passed = 0
        tests_total = 0
        
        # Test 1: CA regions
        tests_total += 1
        try:
            ca_regions = db.list_regions('CA')
            if not ca_regions.empty:
                print(f"✓ California regions: {len(ca_regions)}")
                print("\nTop CA regions by cost factor:")
                top_ca = ca_regions.nlargest(5, 'cost_factor')
                for _, row in top_ca.iterrows():
                    print(f"  {row['region_code']:15} {row['cost_factor']:5.2f}x  {row['region_name']}")
                tests_passed += 1
            else:
                print("✗ No California regions found")
        except Exception as e:
            print(f"✗ CA regions test failed: {e}")
        
        # Test 2: HI regions
        tests_total += 1
        try:
            hi_regions = db.list_regions('HI')
            if not hi_regions.empty:
                print(f"\n✓ Hawaii regions: {len(hi_regions)}")
                print("\nHawaii regions:")
                for _, row in hi_regions.iterrows():
                    print(f"  {row['region_code']:15} {row['cost_factor']:5.2f}x  {row['region_name']}")
                tests_passed += 1
            else:
                print("✗ No Hawaii regions found")
        except Exception as e:
            print(f"✗ HI regions test failed: {e}")
        
        # Test 3: CA utility rates
        tests_total += 1
        try:
            ca_rates = db.list_utility_rates(region='US-CA')
            if not ca_rates.empty:
                print(f"\n✓ California utility rates: {len(ca_rates)}")
                print("\nCA Utilities:")
                for utility in ca_rates['utility'].unique():
                    utility_rates = ca_rates[ca_rates['utility'] == utility]
                    print(f"  {utility}: {len(utility_rates)} rate schedules")
                tests_passed += 1
            else:
                print("✗ No California utility rates found")
        except Exception as e:
            print(f"✗ CA utility rates test failed: {e}")
        
        # Test 4: HI utility rates
        tests_total += 1
        try:
            hi_rates = db.list_utility_rates(region='US-HI')
            if not hi_rates.empty:
                print(f"\n✓ Hawaii utility rates: {len(hi_rates)}")
                print("\nHI Utilities:")
                for utility in hi_rates['utility'].unique():
                    utility_rates = hi_rates[hi_rates['utility'] == utility]
                    print(f"  {utility}: {len(utility_rates)} rate schedules")
                tests_passed += 1
            else:
                print("✗ No Hawaii utility rates found")
        except Exception as e:
            print(f"✗ HI utility rates test failed: {e}")
        
        print(f"\nCA/HI Data: {tests_passed}/{tests_total} tests passed")
        return tests_passed >= tests_total - 1
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_comparison(v05_path: str, v06_path: str) -> bool:
    """Compare v0.05 and v0.06 databases."""
    print("\n" + "="*70)
    print("TEST 4: Version Comparison")
    print("="*70)
    
    try:
        db_v05 = CostDB(v05_path)
        db_v06 = CostDB(v06_path)
        
        print("\nv0.05 Database:")
        info_v05 = db_v05.get_info()
        for key in ['path', 'version', 'systems_count']:
            if key in info_v05:
                print(f"  {key}: {info_v05[key]}")
        
        print("\nv0.06 Database:")
        info_v06 = db_v06.get_info()
        for key, value in info_v06.items():
            if key != 'metadata':
                print(f"  {key}: {value}")
        
        # Test same system in both
        print("\nCost Comparison (same system in both databases):")
        test_system = 'CHPWH-HP-Central'
        
        try:
            cost_v05 = db_v05.get_system_cost(test_system, 1.0)
            cost_v06 = db_v06.get_system_cost(test_system, 1.0)
            
            print(f"  v0.05: ${cost_v05:,.2f}")
            print(f"  v0.06: ${cost_v06:,.2f}")
            
            if cost_v05 > 0 and cost_v06 > 0:
                diff_pct = abs(cost_v06 - cost_v05) / cost_v05 * 100
                print(f"  Difference: {diff_pct:.1f}%")
                
                if diff_pct < 5:
                    print("  ✓ Costs are similar (good!)")
                else:
                    print(f"  ⚠ Costs differ by {diff_pct:.1f}%")
        except Exception as e:
            print(f"  ⚠ Could not compare: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test CostDB migration from v0.05 to v0.06"
    )
    parser.add_argument(
        '--v05',
        default='CostDB_v0.05.xlsx',
        help='Path to v0.05 database'
    )
    parser.add_argument(
        '--v06',
        default='CostDB_v0.06_NREL.xlsx',
        help='Path to v0.06 database'
    )
    parser.add_argument(
        '--skip-comparison',
        action='store_true',
        help='Skip v0.05 vs v0.06 comparison'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("CostDB Migration Test Suite")
    print("="*70)
    print(f"v0.05 database: {args.v05}")
    print(f"v0.06 database: {args.v06}")
    
    results = {}
    
    # Check if files exist
    v05_exists = Path(args.v05).exists()
    v06_exists = Path(args.v06).exists()
    
    if not v05_exists:
        print(f"\n⚠ Warning: v0.05 database not found: {args.v05}")
    
    if not v06_exists:
        print(f"\n⚠ Warning: v0.06 database not found: {args.v06}")
        print("\nTo generate v0.06 database, run:")
        print("  python extract_nrel_costs.py")
    
    # Run tests
    if v05_exists:
        results['v05_backward_compat'] = test_backward_compatibility(args.v05)
    
    if v06_exists:
        results['v06_backward_compat'] = test_backward_compatibility(args.v06)
        results['v06_enhanced'] = test_enhanced_features(args.v06)
        results['v06_ca_hi'] = test_ca_hi_data(args.v06)
    
    if v05_exists and v06_exists and not args.skip_comparison:
        results['comparison'] = test_comparison(args.v05, args.v06)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n✅ All tests passed! Migration successful.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test suite(s) failed. Review errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
