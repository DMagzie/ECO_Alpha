#!/bin/bash
# Download all 22 HBJSON sample files from honeybee-schema

BASE_URL="https://raw.githubusercontent.com/ladybug-tools/honeybee-schema/master/samples/model"

echo "Downloading HBJSON sample files..."

# Simple geometry models
curl -O "$BASE_URL/model_5vertex_sub_faces.hbjson"
curl -O "$BASE_URL/model_5vertex_sub_faces_interior.hbjson"

# Complete models
curl -O "$BASE_URL/model_complete_holes.hbjson"
curl -O "$BASE_URL/model_complete_multiroom_radiance.hbjson"
curl -O "$BASE_URL/model_complete_office_floor.hbjson"
curl -O "$BASE_URL/model_complete_patient_room.hbjson"
curl -O "$BASE_URL/model_complete_user_data.hbjson"

# Energy models
curl -O "$BASE_URL/model_energy_afn.hbjson"
curl -O "$BASE_URL/model_energy_allair_hvac.hbjson"
curl -O "$BASE_URL/model_energy_detailed_loads.hbjson"
curl -O "$BASE_URL/model_energy_fixed_interval.hbjson"
curl -O "$BASE_URL/model_energy_no_program.hbjson"
curl -O "$BASE_URL/model_energy_service_hot_water.hbjson"
curl -O "$BASE_URL/model_energy_window_ac.hbjson"
curl -O "$BASE_URL/model_energy_window_ventilation.hbjson"

# Radiance models
curl -O "$BASE_URL/model_radiance_dynamic_states.hbjson"
curl -O "$BASE_URL/model_radiance_grid_views.hbjson"

# Special cases
curl -O "$BASE_URL/model_with_shade_mesh.hbjson"

echo "Download complete! Total files:"
ls -1 *.hbjson | wc -l
