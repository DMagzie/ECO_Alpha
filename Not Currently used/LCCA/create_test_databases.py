#!/usr/bin/env python3
"""
Create minimal test CostDB files for testing.
"""
import pandas as pd
from datetime import datetime

def create_v05_database():
    """Create minimal v0.05 database."""
    
    # Systems sheet
    systems = pd.DataFrame({
        'system_code': ['CHPWH-HP-Central', 'HP-SPLIT-3T-SEER15', 'GAS-FURNACE-80'],
        'description': ['Central Heat Pump Water Heater', '3-ton Split Heat Pump SEER 15', 'Gas Furnace 80% AFUE'],
        'unit': ['system', 'system', 'system'],
        'unit_cost': [8500.0, 6600.0, 2500.0],
        'source_id': [1, 1, 1],
        'escalation_ref': ['General', 'General', 'General']
    })
    
    # Materials sheet
    materials = pd.DataFrame({
        'material_code': ['COPPER-3/4', 'PEX-1/2', 'DUCT-6IN'],
        'description': ['3/4" Copper Pipe', '1/2" PEX Tubing', '6" Round Duct'],
        'unit': ['ft', 'ft', 'ft'],
        'unit_cost': [8.5, 2.3, 12.0],
        'source_id': [2, 2, 2]
    })
    
    # Markups sheet
    markups = pd.DataFrame({
        'name': ['Overhead', 'Profit', 'Contingency'],
        'percent': [0.15, 0.12, 0.10]
    })
    
    # Escalation sheet
    escalation = pd.DataFrame({
        'name': ['General', 'Energy', 'Labor'],
        'annual_rate': [0.025, 0.030, 0.028]
    })
    
    # Sources sheet
    sources = pd.DataFrame({
        'source_id': [1, 2],
        'name': ['NREL BEopt', 'RSMeans'],
        'agency': ['NREL', 'Gordian'],
        'description': ['BEopt cost database', 'RSMeans construction costs'],
        'data_type': ['System', 'Material'],
        'update_frequency': ['Annual', 'Annual']
    })
    
    # Write to Excel
    with pd.ExcelWriter('CostDB_v0.05.xlsx', engine='openpyxl') as writer:
        systems.to_excel(writer, sheet_name='Systems', index=False)
        materials.to_excel(writer, sheet_name='Materials', index=False)
        markups.to_excel(writer, sheet_name='Markups', index=False)
        escalation.to_excel(writer, sheet_name='Escalation', index=False)
        sources.to_excel(writer, sheet_name='Sources', index=False)
    
    print("✓ Created CostDB_v0.05.xlsx")


def create_v06_database():
    """Create minimal v0.06 database with enhanced features."""
    
    # Metadata sheet
    metadata = pd.DataFrame({
        'database_version': ['0.06'],
        'created_date': [datetime.now().strftime('%Y-%m-%d')],
        'source': ['Test Database'],
        'description': ['Enhanced CostDB with CA/HI data']
    })
    
    # System_Costs sheet (enhanced)
    system_costs = pd.DataFrame({
        'system_id': ['CHPWH-HP-Central', 'HP-SPLIT-3T-SEER15', 'HP-SPLIT-2T-SEER15', 
                      'GAS-FURNACE-80', 'PV-5KW', 'BATTERY-10KWH'],
        'system_name': ['Central HPWH', '3-ton Heat Pump', '2-ton Heat Pump',
                       'Gas Furnace', '5kW PV System', '10kWh Battery'],
        'category': ['DHW', 'HVAC', 'HVAC', 'HVAC', 'Solar', 'Storage'],
        'sub_category': ['CHPWH', 'HeatPump', 'HeatPump', 'Furnace', 'PV', 'Battery'],
        'unit': ['system', 'system', 'system', 'system', 'system', 'system'],
        'installed_cost': [8500.0, 6600.0, 5200.0, 2500.0, 12500.0, 8000.0],
        'source': ['NREL', 'NREL', 'NREL', 'NREL', 'NREL ATB', 'NREL ATB']
    })
    
    # Material_Costs sheet (enhanced)
    material_costs = pd.DataFrame({
        'material_id': ['COPPER-3/4', 'PEX-1/2', 'DUCT-6IN'],
        'material_name': ['3/4" Copper Pipe', '1/2" PEX Tubing', '6" Round Duct'],
        'unit': ['ft', 'ft', 'ft'],
        'unit_cost': [8.5, 2.3, 12.0],
        'source': ['RSMeans', 'RSMeans', 'RSMeans']
    })
    
    # Regional_Factors sheet
    regional_factors = pd.DataFrame({
        'region_code': ['US', 'US-CA', 'US-CA-SF', 'US-CA-SJ', 'US-CA-OAK', 
                       'US-CA-LA', 'US-CA-SD', 'US-HI', 'US-HI-HON', 'US-HI-MAU'],
        'region_name': ['US Average', 'California', 'San Francisco', 'San Jose', 'Oakland',
                       'Los Angeles', 'San Diego', 'Hawaii', 'Honolulu', 'Maui'],
        'cost_factor': [1.00, 1.25, 1.38, 1.36, 1.35, 1.22, 1.20, 1.45, 1.45, 1.50],
        'source': ['Baseline'] + ['RSMeans'] * 9
    })
    
    # Utility_Rates sheet
    utility_rates = pd.DataFrame({
        'rate_id': ['PGE-E1-TIER', 'PGE-E-TOU-C', 'SCE-TOU-D-4-9PM', 
                   'SDGE-DR-TIER', 'HECO-R-TIER', 'MECO-R-TIER'],
        'utility': ['PG&E', 'PG&E', 'SCE', 'SDG&E', 'HECO', 'MECO'],
        'rate_name': ['E-1 Tiered Residential', 'E-TOU-C Time-of-Use', 
                     'TOU-D-4-9PM', 'DR Tiered', 'Residential Tiered', 'Residential Tiered'],
        'structure_type': ['tiered', 'tou', 'tou', 'tiered', 'tiered', 'tiered'],
        'region_code': ['US-CA-SF', 'US-CA-SF', 'US-CA-LA', 'US-CA-SD', 'US-HI-HON', 'US-HI-MAU'],
        'tier_structure': ['{"tiers": [0.25, 0.32, 0.38]}'] * 3 + ['{"tiers": [0.28, 0.35]}'] * 3,
        'tou_structure': [None, '{"peak": 0.45, "off_peak": 0.22}', '{"peak": 0.42, "off_peak": 0.20}', None, None, None]
    })
    
    # Systems sheet (legacy, for compatibility)
    systems = pd.DataFrame({
        'system_code': ['CHPWH-HP-Central', 'HP-SPLIT-3T-SEER15', 'GAS-FURNACE-80'],
        'description': ['Central Heat Pump Water Heater', '3-ton Split Heat Pump SEER 15', 'Gas Furnace 80% AFUE'],
        'unit': ['system', 'system', 'system'],
        'unit_cost': [8500.0, 6600.0, 2500.0],
        'source_id': [1, 1, 1],
        'escalation_ref': ['General', 'General', 'General']
    })
    
    # Materials sheet (legacy, for compatibility)
    materials = pd.DataFrame({
        'material_code': ['COPPER-3/4', 'PEX-1/2', 'DUCT-6IN'],
        'description': ['3/4" Copper Pipe', '1/2" PEX Tubing', '6" Round Duct'],
        'unit': ['ft', 'ft', 'ft'],
        'unit_cost': [8.5, 2.3, 12.0],
        'source_id': [2, 2, 2]
    })
    
    # Markups sheet
    markups = pd.DataFrame({
        'name': ['Overhead', 'Profit', 'Contingency'],
        'percent': [0.15, 0.12, 0.10]
    })
    
    # Escalation sheet
    escalation = pd.DataFrame({
        'name': ['General', 'Energy', 'Labor'],
        'annual_rate': [0.025, 0.030, 0.028]
    })
    
    # Sources sheet
    sources = pd.DataFrame({
        'source_id': [1, 2],
        'name': ['NREL BEopt', 'RSMeans'],
        'agency': ['NREL', 'Gordian'],
        'description': ['BEopt cost database', 'RSMeans construction costs'],
        'data_type': ['System', 'Material'],
        'update_frequency': ['Annual', 'Annual']
    })
    
    # Write to Excel
    with pd.ExcelWriter('CostDB_v0.06_NREL.xlsx', engine='openpyxl') as writer:
        metadata.to_excel(writer, sheet_name='Metadata', index=False)
        system_costs.to_excel(writer, sheet_name='System_Costs', index=False)
        material_costs.to_excel(writer, sheet_name='Material_Costs', index=False)
        regional_factors.to_excel(writer, sheet_name='Regional_Factors', index=False)
        utility_rates.to_excel(writer, sheet_name='Utility_Rates', index=False)
        systems.to_excel(writer, sheet_name='Systems', index=False)
        materials.to_excel(writer, sheet_name='Materials', index=False)
        markups.to_excel(writer, sheet_name='Markups', index=False)
        escalation.to_excel(writer, sheet_name='Escalation', index=False)
        sources.to_excel(writer, sheet_name='Sources', index=False)
    
    print("✓ Created CostDB_v0.06_NREL.xlsx")


if __name__ == '__main__':
    print("Creating test CostDB databases...\n")
    create_v05_database()
    create_v06_database()
    print("\n✓ Test databases created successfully!")
