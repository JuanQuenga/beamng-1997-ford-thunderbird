# References and modeling assumptions

References were checked on November 7, 2026.

## Vehicle references

- [Ford's 1997 Thunderbird sales brochure](https://www.auto-brochures.com/makes/Ford/Thunderbird/Ford_US%20Thunderbird_1997.pdf) supplies the exterior and interior reference, available engines, nominal horsepower, automatic transmission, four-wheel independent suspension, and wheel options. Page 10 lists the equipment and output.
- [Ford's 1997 Thunderbird owner's guide](https://www.fordservicecontent.com/Ford_Content/catalog/owner_guides/97tbrog1e.pdf) documents the engines, 4R70W transmission, and 68.1 L fuel capacity.
- [1997 Thunderbird V8 specifications](https://www.kbb.com/ford/thunderbird/1997/lx-coupe-2d/) list the nominal V8 peak-power speed. The V8 curve uses 4250 RPM as a target.

The project does not include brochure scans or downloaded third-party car meshes in either distribution ZIP. Geometry and scripts were created for this project.

The torque curves between reference points, physical masses, spring rates, damping, wheel friction, gear-change settings, and axle ratios are estimates. The model is a simplified visual approximation. It was not traced from measured blueprints or a scan. Metadata output describes the intended prototype, not a measurement from BeamNG.

## BeamNG references

- [Vehicle modeling guidelines](https://documentation.beamng.com/modding/vehicle/vehicle_modeling/) describe COLLADA export and vehicle mesh conventions.
- [JBeam file sections](https://documentation.beamng.com/modding/vehicle/sections/) describe structural elements and vehicle systems.
- [Pressure wheels](https://documentation.beamng.com/modding/vehicle/sections/wheels/) describe tire construction, wheel groups, axle endpoints, and braking settings.
- [Hydros](https://documentation.beamng.com/modding/vehicle/sections/hydros/) describe the variable-length steering links.
- [Configuration and info files](https://documentation.beamng.com/modding/vehicle/tutorials/configs/) describe configuration names, paint selection, metadata fields, and units. In particular, `Power` uses kilowatts.
- [BeamNG 0.40 announcement](https://www.beamng.com/game/news/blog/beamng-drive-v0-40/) identifies the target release series. Compatibility with later changes requires another game test.

The official Basic Car Tutorial template was inspected for file-format examples. Its meshes and JBeam files are not included in this vehicle.

## RLS references

The source check targets [RLS Career Overhaul 2.8.0](https://github.com/RLS-Modding/rls_career_overhaul/releases/tag/v2.8.0). This release targets BeamNG 0.40.3. The local source check uses its release tag, rather than an unpinned development branch.

The inspected RLS modules include:

- `vehicleShopping/catalog.lua`, for dealer attribute filters.
- `vehicleShopping/validation.lua`, for vehicle metadata shape checks.
- `vehicleShopping/populationSelector.lua`, for population weights.
- `usedVehicleCondition.lua`, for year ranges.
- `valueCalculator.lua`, for parts-derived vehicle valuation.
- `partShopping.lua`, for part-slot behavior.
- `dealerships.facilities.json`, for the released map's seller filters.

The vehicle has positive part prices, stable named slots, matching PC configurations, and nonzero population weights. Population values are chosen spawn weights, not historical production totals. RLS calculates actual purchase and repair prices using its economy and condition rules.

The Lua check loads the real filter functions outside BeamNG. It supplies generated metadata in the shape expected after vehicle discovery. Successful filtering does not prove that game discovery, dealerships, repairs, engine certification, or career saves work correctly.
