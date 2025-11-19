#!/usr/bin/env python3
"""Debug what's in proj_metadata"""
import json

from eco_tools.translators.cibd22x import CIBD22XImporter

cibd22x_file = "/Users/DavidM/Documents/ECO_Alpha_v7/reference_data/cbecc/CBECC Models/Bressi Ranch/Bressi Ranch Apartments.cibd22x"

print("Importing CIBD22X...")
importer = CIBD22XImporter()
internal = importer.import_file(cibd22x_file)

print("\nproj_metadata contents:")
print(json.dumps(internal.proj_metadata, indent=2, default=str)[:2000])
