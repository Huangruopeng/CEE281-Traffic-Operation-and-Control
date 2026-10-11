# Component interfaces

All modules use seconds and metres internally. CSV fields are stable exchange interfaces; unavailable quantities are blank/`NaN` and paired with a quality flag.

## Vehicle state

`time_s, vehicle_id, lane_id, position_m, speed_mps, acceleration_mps2, controller, equipped`

Origin is the upstream mainline boundary (`position_m = 0`); position increases downstream. Vehicle identifiers remain stable from entry through exit. States are logged every 0.5 s for the disturbance cohort and the ramp area.

## Observation

`sensor_id, interval_start_s, interval_end_s, count, mean_speed_mps, occupancy_pct, quality_flag`

Counts use the half-open convention `(interval_start_s, interval_end_s]`. Mean speed is available only when at least one crossing occurs. `occupancy_pct` is the time-mean fraction of a 50-m virtual detector zone covered by 5-m vehicles. Missing-test records explicitly use `quality_flag = missing` with blank measured quantities.

## Estimate and forecast

`issue_time_s, target_time_s, segment_id, variable_name, units, method, estimated_state, predicted_value, quality_indicator`

The state is a smoothed 30-s vehicle count. The forecast horizon is exactly one detector interval (30 s). A missing input leaves the previous smoothing state unchanged and sets `quality_indicator = missing_input_hold`.

## Ramp control command

`issue_time_s, apply_time_s, actuator_id, action, value, units, lower_bound, upper_bound, fallback_active, reason, queue_estimate_veh`

The actuator is `ramp_meter_R1`. Commands are release rates in vehicles/hour, bounded to 240-900 veh/h. Missing observations select the fixed 480-veh/h fallback. A 25-vehicle queue invokes storage protection.

## Vehicle control command

`issue_time_s, apply_time_s, vehicle_id, controller, measured_ego_speed_mps, measured_gap_m, measured_relative_speed_mps, communicated_predecessor_accel_mps2, message_valid, message_age_s, command_mps2, bounded_min_mps2, bounded_max_mps2, fallback_state`

ACC uses local gap, ego speed, and relative speed. CACC additionally uses only the immediate equipped predecessor's delayed acceleration message. A dropped, unavailable, or stale message causes `ACC_fallback`; future trajectory and simulator truth are not controller inputs. After the nominal law, a safety supervisor limits commands when one-step prediction or stopping distance would consume the configured 2.0-m physical clearance. Such rows use `fallback_state = safety_override`.

## Evaluation record

`scenario_id, demand_id, seed, model_version, controller_version, controller, penetration, comm_delay_s, dropout_probability, dt_s` plus throughput, delay, boundary/residual queues, minimum gap, hard-brake count, safety-intervention count, final collision-guard activation count, message statistics, and disturbance amplification.

