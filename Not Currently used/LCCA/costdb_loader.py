"""
Load and query the CostDB Excel (v0.05 or v0.06).

BACKWARD COMPATIBLE: Works with existing v0.05 files.
ENHANCED: Adds CA/HI regional factors, utility rates, parametric costing.

Expected sheets (v0.05 - required):
- Systems (system_code, description, unit, unit_cost, source_id, escalation_ref)
- Materials (...)
- Markups (name, percent)
- Escalation (name, annual_rate)
- Sources (source_id, name, agency, description, data_type, update_frequency)

Additional sheets (v0.06 - optional):
- Regional_Factors (region_code, region_name, cost_factor, source)
- Utility_Rates (rate_id, utility, rate_name, structure_type, ...)
- System_Costs (enhanced format with category, sub_category)
- Material_Costs (enhanced format)
"""
from __future__ import annotations
import pandas as pd
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class CostDB:
    """
    Enhanced CostDB loader with backward compatibility.
    
    Usage Examples:
    
    # Legacy v0.05 usage (still works):
    db = CostDB('CostDB_v0.05.xlsx')
    cost = db.get_system_cost('CHPWH-HP-Central', 1.0)
    
    # Enhanced v0.06 usage:
    db = CostDB('CostDB_v0.06_NREL.xlsx')
    cost = db.get_system_cost_with_region('HP-SPLIT-3T-SEER15', 1.0, 'US-CA-SF')
    rate = db.get_utility_rate('PGE-E1-TIER')
    """
    
    def __init__(self, path: str):
        self.path = Path(path)
        self.version = 'unknown'
        
        # Load core sheets (required, v0.05 compatible)
        try:
            self.systems = pd.read_excel(path, sheet_name="Systems")
            self.materials = pd.read_excel(path, sheet_name="Materials")
            self.markups = pd.read_excel(path, sheet_name="Markups")
            self.escalation = pd.read_excel(path, sheet_name="Escalation")
            self.sources = pd.read_excel(path, sheet_name="Sources")
            self.version = 'v0.05'
        except Exception as e:
            raise ValueError(f"Failed to load core CostDB sheets: {e}")
        
        # Try to load enhanced sheets (optional, v0.06)
        self.regional_factors = None
        self.utility_rates = None
        self.system_costs_enhanced = None
        self.material_costs_enhanced = None
        
        try:
            self.regional_factors = pd.read_excel(path, sheet_name="Regional_Factors")
            print(f"✓ Loaded Regional_Factors: {len(self.regional_factors)} regions")
            self.version = 'v0.06'
        except:
            print("ℹ Regional_Factors not found (v0.05 mode)")
        
        try:
            self.utility_rates = pd.read_excel(path, sheet_name="Utility_Rates")
            print(f"✓ Loaded Utility_Rates: {len(self.utility_rates)} rates")
        except:
            print("ℹ Utility_Rates not found (v0.05 mode)")
        
        try:
            # v0.06 has enhanced System_Costs sheet
            self.system_costs_enhanced = pd.read_excel(path, sheet_name="System_Costs")
            print(f"✓ Loaded System_Costs (enhanced): {len(self.system_costs_enhanced)} systems")
        except:
            # Use legacy Systems sheet
            self.system_costs_enhanced = None
        
        try:
            self.material_costs_enhanced = pd.read_excel(path, sheet_name="Material_Costs")
            print(f"✓ Loaded Material_Costs (enhanced): {len(self.material_costs_enhanced)} materials")
        except:
            self.material_costs_enhanced = None
        
        try:
            self.metadata = pd.read_excel(path, sheet_name="Metadata")
            print(f"✓ CostDB version: {self.metadata['database_version'].iloc[0]}")
        except:
            self.metadata = None
        
        print(f"✓ CostDB loaded: {self.version} mode\n")
    
    # =========================================================================
    # LEGACY METHODS (v0.05 compatible - DO NOT CHANGE)
    # =========================================================================
    
    def get_system_cost(self, system_code: str, quantity: float) -> float:
        """
        LEGACY METHOD (v0.05 compatible).
        
        Get system cost by code and quantity.
        Works with both v0.05 'Systems' sheet and v0.06 'System_Costs' sheet.
        
        Args:
            system_code: System code (e.g., 'CHPWH-HP-Central')
            quantity: Quantity to multiply by unit cost
            
        Returns:
            Total cost (float)
        """
        # Try enhanced sheet first (v0.06)
        if self.system_costs_enhanced is not None:
            # v0.06: Look in System_Costs by system_id
            row = self.system_costs_enhanced[
                self.system_costs_enhanced["system_id"] == system_code
            ]
            if not row.empty:
                unit_cost = float(row["installed_cost"].iloc[0])
                return quantity * unit_cost
        
        # Fall back to legacy Systems sheet (v0.05)
        row = self.systems[self.systems["system_code"] == system_code]
        if row.empty:
            print(f"⚠ Warning: System code '{system_code}' not found")
            return 0.0
        
        unit_cost = float(row["unit_cost"].iloc[0])
        return quantity * unit_cost

    def get_markup_multiplier(self) -> float:
        """
        LEGACY METHOD (v0.05 compatible).
        
        Get total markup multiplier from Markups sheet.
        Returns 1.0 + sum(all markup percentages)
        """
        pct = self.markups["percent"].fillna(0.0).sum()
        return 1.0 + pct

    def get_escalation_rate(self, name: str = "General") -> float:
        """
        LEGACY METHOD (v0.05 compatible).
        
        Get escalation rate by name.
        """
        row = self.escalation[self.escalation["name"] == name]
        if row.empty:
            print(f"⚠ Warning: Escalation '{name}' not found, using 0.0")
            return 0.0
        return float(row["annual_rate"].iloc[0])
    
    # =========================================================================
    # ENHANCED METHODS (v0.06 features)
    # =========================================================================
    
    def get_system_cost_with_region(
        self, 
        system_code: str, 
        quantity: float, 
        region: str = 'US',
        apply_markups: bool = False
    ) -> Dict:
        """
        ENHANCED METHOD (v0.06).
        
        Get system cost with regional adjustment.
        
        Args:
            system_code: System code or system_id
            quantity: Quantity
            region: Region code (e.g., 'US-CA-SF')
            apply_markups: Whether to apply markup factors
            
        Returns:
            Dict with detailed cost breakdown
        """
        # Get base cost (works with v0.05 or v0.06)
        base_cost = self.get_system_cost(system_code, quantity)
        
        if base_cost == 0.0:
            return {
                'system_code': system_code,
                'quantity': quantity,
                'base_cost': 0.0,
                'regional_factor': 1.0,
                'regional_cost': 0.0,
                'total': 0.0,
                'region': region,
                'error': 'System not found'
            }
        
        # Apply regional factor (if available)
        regional_factor = self.get_regional_factor(region)
        regional_cost = base_cost * regional_factor
        
        # Apply markups if requested
        if apply_markups:
            markup_multiplier = self.get_markup_multiplier()
            total = regional_cost * markup_multiplier
        else:
            total = regional_cost
        
        return {
            'system_code': system_code,
            'quantity': quantity,
            'base_cost': base_cost,
            'regional_factor': regional_factor,
            'regional_cost': regional_cost,
            'markup_multiplier': self.get_markup_multiplier() if apply_markups else 1.0,
            'total': total,
            'region': region,
            'unit_cost': base_cost / quantity if quantity > 0 else 0.0
        }
    
    def get_regional_factor(self, region_code: str) -> float:
        """
        Get regional cost adjustment factor.
        
        Args:
            region_code: Region code (e.g., 'US-CA-SF')
            
        Returns:
            Cost factor (1.0 = baseline)
        """
        if self.regional_factors is None:
            # No regional data, return baseline
            return 1.0
        
        # Exact match
        factor_row = self.regional_factors[
            self.regional_factors['region_code'] == region_code
        ]
        
        if not factor_row.empty:
            return float(factor_row['cost_factor'].iloc[0])
        
        # Try parent region (e.g., US-CA from US-CA-SF)
        if '-' in region_code:
            parts = region_code.split('-')
            for i in range(len(parts) - 1, 0, -1):
                parent = '-'.join(parts[:i])
                factor_row = self.regional_factors[
                    self.regional_factors['region_code'] == parent
                ]
                if not factor_row.empty:
                    print(f"ℹ Using parent region '{parent}' for '{region_code}'")
                    return float(factor_row['cost_factor'].iloc[0])
        
        # Default to baseline
        print(f"⚠ Region '{region_code}' not found, using 1.0x")
        return 1.0
    
    def get_utility_rate(self, rate_id: str = None, **filters) -> Optional[Dict]:
        """
        Get utility rate structure by ID or filters.
        
        Args:
            rate_id: Rate ID (e.g., 'PGE-E1-TIER')
            **filters: Optional filters (utility='PG&E', region_code='US-CA-SF')
            
        Returns:
            Rate structure dict or None
        """
        if self.utility_rates is None:
            print("⚠ Utility rates not available (v0.05 mode)")
            return None
        
        df = self.utility_rates.copy()
        
        # Filter by rate_id
        if rate_id:
            df = df[df['rate_id'] == rate_id]
        
        # Additional filters
        for key, value in filters.items():
            if key in df.columns:
                df = df[df[key] == value]
        
        if df.empty:
            print(f"⚠ No utility rate found for: {rate_id or filters}")
            return None
        
        # Convert to dict
        rate = df.iloc[0].to_dict()
        
        # Parse JSON fields if present
        for field in ['tier_structure', 'tou_structure']:
            if field in rate and pd.notna(rate[field]):
                try:
                    rate[field] = json.loads(rate[field])
                except:
                    pass
        
        return rate
    
    def list_utility_rates(self, region: str = None, utility: str = None) -> pd.DataFrame:
        """
        List available utility rates.
        
        Args:
            region: Filter by region (e.g., 'US-CA-SF')
            utility: Filter by utility (e.g., 'PG&E')
            
        Returns:
            DataFrame of available rates
        """
        if self.utility_rates is None:
            return pd.DataFrame()
        
        df = self.utility_rates.copy()
        
        if region:
            df = df[df['region_code'].str.contains(region, na=False)]
        
        if utility:
            df = df[df['utility'] == utility]
        
        # Return simplified view
        cols = ['rate_id', 'utility', 'rate_name', 'structure_type', 'region_code']
        return df[[c for c in cols if c in df.columns]]
    
    def list_regions(self, state: str = None) -> pd.DataFrame:
        """
        List available regions.
        
        Args:
            state: Filter by state code (e.g., 'CA', 'HI')
            
        Returns:
            DataFrame of regions
        """
        if self.regional_factors is None:
            return pd.DataFrame()
        
        df = self.regional_factors.copy()
        
        if state:
            df = df[df['region_code'].str.contains(f'US-{state}', na=False)]
        
        return df[['region_code', 'region_name', 'cost_factor', 'source']]
    
    def query_systems(
        self,
        category: str = None,
        sub_category: str = None,
        system_id_pattern: str = None
    ) -> pd.DataFrame:
        """
        Query systems by category or pattern.
        
        Args:
            category: Filter by category (e.g., 'HVAC', 'DHW')
            sub_category: Filter by sub-category (e.g., 'HeatPump', 'CHPWH')
            system_id_pattern: Filter by ID pattern (e.g., 'HP-SPLIT')
            
        Returns:
            DataFrame of matching systems
        """
        if self.system_costs_enhanced is not None:
            df = self.system_costs_enhanced.copy()
            
            if category and 'category' in df.columns:
                df = df[df['category'] == category]
            
            if sub_category and 'sub_category' in df.columns:
                df = df[df['sub_category'] == sub_category]
            
            if system_id_pattern and 'system_id' in df.columns:
                df = df[df['system_id'].str.contains(system_id_pattern, na=False)]
            
            cols = ['system_id', 'system_name', 'category', 'sub_category', 
                   'unit', 'installed_cost', 'source']
            return df[[c for c in cols if c in df.columns]]
        
        # Fall back to legacy systems
        df = self.systems.copy()
        
        if system_id_pattern and 'system_code' in df.columns:
            df = df[df['system_code'].str.contains(system_id_pattern, na=False)]
        
        return df
    
    def estimate_system_cost_parametric(
        self,
        system_type: str,
        capacity: float,
        region: str = 'US',
        capacity_unit: str = 'tons'
    ) -> Dict:
        """
        Parametric cost estimation when exact system not in database.
        
        Uses typical $/unit costs with economy of scale adjustments.
        
        Args:
            system_type: System type (e.g., 'SplitHP', 'CHPWH', 'PV')
            capacity: Capacity value
            region: Region code
            capacity_unit: Unit of capacity (tons, kW, gallons, etc.)
            
        Returns:
            Cost estimate dict
        """
        # Typical costs (baseline, US average)
        # These are placeholder values - should be in database
        PARAMETRIC_COSTS = {
            'SplitHP': {'unit': 'ton', 'cost_per_unit': 2200, 'scale_exp': 0.9},
            'PTHP': {'unit': 'ton', 'cost_per_unit': 1500, 'scale_exp': 0.85},
            'GasFurnace': {'unit': 'MBH', 'cost_per_unit': 50, 'scale_exp': 0.9},
            'CHPWH': {'unit': 'gallon', 'cost_per_unit': 140, 'scale_exp': 0.85},
            'HPWH': {'unit': 'gallon', 'cost_per_unit': 35, 'scale_exp': 1.0},
            'PV': {'unit': 'kWdc', 'cost_per_unit': 2500, 'scale_exp': 0.95},
            'Battery': {'unit': 'kWh', 'cost_per_unit': 800, 'scale_exp': 0.95},
        }
        
        if system_type not in PARAMETRIC_COSTS:
            return {
                'error': f"System type '{system_type}' not in parametric model",
                'total': 0.0
            }
        
        params = PARAMETRIC_COSTS[system_type]
        
        # Base cost with economy of scale
        # Cost = base_cost_per_unit * capacity^scale_exponent
        base_cost = params['cost_per_unit'] * (capacity ** params['scale_exp'])
        
        # Apply regional factor
        regional_factor = self.get_regional_factor(region)
        regional_cost = base_cost * regional_factor
        
        return {
            'system_type': system_type,
            'capacity': capacity,
            'capacity_unit': params['unit'],
            'base_cost_per_unit': params['cost_per_unit'],
            'scale_exponent': params['scale_exp'],
            'base_cost': base_cost,
            'regional_factor': regional_factor,
            'regional_cost': regional_cost,
            'total': regional_cost,
            'region': region,
            'method': 'parametric',
            'note': 'Parametric estimate - use actual quotes for final design'
        }
    
    def get_info(self) -> Dict:
        """Get database information and statistics."""
        info = {
            'path': str(self.path),
            'version': self.version,
            'features': []
        }
        
        if self.systems is not None:
            info['systems_count'] = len(self.systems)
            info['features'].append('Systems (v0.05)')
        
        if self.system_costs_enhanced is not None:
            info['system_costs_count'] = len(self.system_costs_enhanced)
            info['features'].append('System_Costs (enhanced)')
        
        if self.regional_factors is not None:
            info['regions_count'] = len(self.regional_factors)
            info['features'].append('Regional_Factors')
        
        if self.utility_rates is not None:
            info['utility_rates_count'] = len(self.utility_rates)
            info['features'].append('Utility_Rates')
        
        if self.materials is not None:
            info['materials_count'] = len(self.materials)
        
        if self.metadata is not None:
            meta = self.metadata.iloc[0].to_dict()
            info['metadata'] = {k: v for k, v in meta.items() if pd.notna(v)}
        
        return info


# =========================================================================
# UTILITY FUNCTIONS
# =========================================================================

def compare_costdb_versions(v05_path: str, v06_path: str):
    """
    Compare two CostDB versions to verify compatibility.
    
    Args:
        v05_path: Path to v0.05 database
        v06_path: Path to v0.06 database
    """
    print("Comparing CostDB versions...\n")
    
    db_v05 = CostDB(v05_path)
    db_v06 = CostDB(v06_path)
    
    print("\n" + "="*60)
    print("v0.05 Info:")
    print("="*60)
    for key, value in db_v05.get_info().items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*60)
    print("v0.06 Info:")
    print("="*60)
    for key, value in db_v06.get_info().items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*60)
    print("Compatibility Test:")
    print("="*60)
    
    # Test backward compatibility
    test_system = 'CHPWH-HP-Central'
    test_qty = 1.0
    
    try:
        cost_v05 = db_v05.get_system_cost(test_system, test_qty)
        print(f"✓ v0.05 get_system_cost(): ${cost_v05:,.2f}")
    except Exception as e:
        print(f"✗ v0.05 failed: {e}")
    
    try:
        cost_v06 = db_v06.get_system_cost(test_system, test_qty)
        print(f"✓ v0.06 get_system_cost(): ${cost_v06:,.2f}")
    except Exception as e:
        print(f"✗ v0.06 failed: {e}")
    
    # Test new features
    if db_v06.regional_factors is not None:
        print(f"✓ v0.06 has regional factors: {len(db_v06.regional_factors)} regions")
        
        # Test regional cost
        cost_regional = db_v06.get_system_cost_with_region(
            test_system, test_qty, 'US-CA-SF'
        )
        print(f"✓ v0.06 regional cost (SF): ${cost_regional['total']:,.2f}")
    
    if db_v06.utility_rates is not None:
        print(f"✓ v0.06 has utility rates: {len(db_v06.utility_rates)} rates")


# =========================================================================
# EXAMPLE USAGE
# =========================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "CostDB_v0.06_NREL.xlsx"
    
    print("="*60)
    print("CostDB Loader Test")
    print("="*60)
    print(f"Loading: {db_path}\n")
    
    # Load database
    db = CostDB(db_path)
    
    # Display info
    print("\n" + "="*60)
    print("Database Info:")
    print("="*60)
    info = db.get_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Test legacy method
    print("\n" + "="*60)
    print("Test 1: Legacy get_system_cost()")
    print("="*60)
    cost = db.get_system_cost('HP-SPLIT-3T-SEER15', 1.0)
    print(f"  3-ton heat pump: ${cost:,.2f}")
    
    # Test enhanced method
    if db.version == 'v0.06':
        print("\n" + "="*60)
        print("Test 2: Enhanced get_system_cost_with_region()")
        print("="*60)
        
        regions = ['US', 'US-CA', 'US-CA-SF', 'US-HI-HON']
        for region in regions:
            result = db.get_system_cost_with_region(
                'HP-SPLIT-3T-SEER15', 1.0, region
            )
            print(f"  {region:12} → ${result['total']:>8,.0f} " +
                  f"({result['regional_factor']:.2f}x)")
        
        # Test utility rates
        print("\n" + "="*60)
        print("Test 3: Utility Rates")
        print("="*60)
        
        # List CA rates
        ca_rates = db.list_utility_rates(region='US-CA')
        print(f"\nCA Utility Rates ({len(ca_rates)}):")
        print(ca_rates.to_string(index=False))
        
        # Get specific rate
        pge_rate = db.get_utility_rate('PGE-E1-TIER')
        if pge_rate:
            print(f"\nPG&E E-1 Rate Details:")
            print(f"  Utility: {pge_rate['utility']}")
            print(f"  Name: {pge_rate['rate_name']}")
            print(f"  Type: {pge_rate['structure_type']}")
        
        # Test parametric estimation
        print("\n" + "="*60)
        print("Test 4: Parametric Cost Estimation")
        print("="*60)
        
        hp_estimate = db.estimate_system_cost_parametric(
            'SplitHP', 3.0, 'US-CA-SF', 'tons'
        )
        print(f"  3-ton HP in SF (parametric): ${hp_estimate['total']:,.0f}")
        
        pv_estimate = db.estimate_system_cost_parametric(
            'PV', 50.0, 'US-HI-HON', 'kWdc'
        )
        print(f"  50 kW PV in Honolulu (parametric): ${pv_estimate['total']:,.0f}")
    
    print("\n" + "="*60)
    print("✓ All tests complete!")
    print("="*60)
