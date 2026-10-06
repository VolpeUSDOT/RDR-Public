import os
import sys
import datetime
import pandas as pd
import numpy as np
import params
import streamlit as st

import gui_tools as ut

def main():
    st.set_page_config(page_title="RDR Parameters", page_icon="C:\GitHub\RDR\gui\__siteIcon__ .ico")
    st.logo("C:\GitHub\RDR\gui\__siteIcon__ .ico")

    st.title("**Parameters**", width="content", text_alignment="justify")
    st.caption(f"Currently loaded: {params.save_file.value}")

    params.save_folder.value = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves")

    left, lmiddle, rmiddle, right = st.columns(4, gap=None)

    if left.button("Load save 📂", width="stretch", type="tertiary"):
        ut.load_save_dialog()

    if lmiddle.button("Save 💾", width="stretch", type="tertiary"):
        if params.save_file is None:
            # state_save(params.save_folder, params.save_name, param_list, go_to)
            ut.save_as_dialog()
        
        elif params.save_file.value is None or params.save_file.value == "":
            # state_save(params.save_folder, params.save_name, param_list, go_to)
            ut.save_as_dialog()

        else:
            ut.quick_save_dialog()

    if rmiddle.button("Save as 📝", width="stretch", type="tertiary"):
        ut.save_as_dialog()

    if right.button("Clear all ❌", width="stretch", type="tertiary"):
        ut.clear_all()

    # ===================
    # COMMON VALUES
    # ===================

    st.header(":primary[General] RDR Configuration")
    st.html(
        """Contains user parameters for:
        <br>(1) identifying input and output directories,
        <br>(2) specifying scenario analysis framework,
        <br>(3) defining regression model process,
        <br>(4) defining disruption analysis,
        <br>(5) defining recovery process,
        <br>(6) calculating ROI metrics.""")
    
    section_number = 0
    element_number = 0

    section_number += 1
    st.header(f"{section_number}. Common Values", divider="gray")
    with st.expander("Input and output directory, run ID, and years"):

        parameter = params.input_dir
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        ut.input_dir_text_input(display, parameter)
        ut.create_display_echo(parameter)

        parameter = params.output_dir
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.run_id
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        st.markdown("")

        left, right = st.columns(2)

        current_year = datetime.datetime.today().year

        with left:
            parameter = params.analysis_period_start_year
            element_number += 1
            display = ut.create_display_name(parameter, section=section_number, element=element_number)   
            st.number_input(display, min_value=1900, max_value=3000, step=1, value=parameter.value, key=parameter.name)
            parameter.value = st.session_state[parameter.name]
            ut.create_display_echo(parameter)

            parameter = params.core_model_run_initial_year
            element_number += 1
            display = ut.create_display_name(parameter, section=section_number, element=element_number)   
            st.number_input(display, min_value=1900, max_value=3000, step=1, value=parameter.value, key=parameter.name)
            parameter.value = st.session_state[parameter.name]
            ut.create_display_echo(parameter)

        with right:
            parameter = params.analysis_period_end_year
            element_number += 1
            display = ut.create_display_name(parameter, section=section_number, element=element_number)   
            st.number_input(display, min_value=1900, max_value=3000, step=1, value=parameter.value, key=parameter.name)
            parameter.value = st.session_state[parameter.name]
            ut.create_display_echo(parameter)

            parameter = params.core_model_run_future_year
            element_number += 1
            display = ut.create_display_name(parameter, section=section_number, element=element_number)   
            st.number_input(display, min_value=1900, max_value=3000, step=1, value=parameter.value, key=parameter.name)
            parameter.value = st.session_state[parameter.name]
            ut.create_display_echo(parameter)

    # ===================
    # METAMODEL VALUES
    # ===================

    element_number = 0
    section_number += 1
    st.header(f"{section_number}. Metamodel", divider="green")
    with st.expander("Metamodel type, LHS sample target, and AequilibraE settings"):
        parameter = params.metamodel_type
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.calc_transit_metrics
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.aeq_run_type
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.run_minieq
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.allow_centroid_flows
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.lhs_sample_target
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, min_value=0, max_value=10000, step=1, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.aeq_max_iter
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, min_value=0, step=1, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.aeq_rgap_target
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, min_value=0.000, step=0.001, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

    # ===================
    # DISRUPTION VALUES
    # ===================

    element_number = 0
    section_number += 1
    st.header(f"{section_number}. Disruption", divider="red")
    with st.expander("Link availability, alpha, beta, upper and lower bounds, and mitigation approach"):
        parameter = params.link_availability_approach
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)    
        st.pills(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.link_availability_csv ## Conditional requirement
        if params.link_availability_approach.value == 'manual' or params.link_availability_approach.value == 'facility_type_manual':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        l, ml, mr, r = st.columns(4)

        # with l:
        parameter = params.alpha ## Conditional requirement
        if params.link_availability_approach.value == 'beta_distribution_function':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with ml:
        parameter = params.beta ## Conditional requirement
        if params.link_availability_approach.value == 'beta_distribution_function':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with mr:
        parameter = params.lower_bound ## Conditional requirement
        if params.link_availability_approach.value == 'beta_distribution_function':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with r:
        parameter = params.upper_bound ## Conditional requirement
        if params.link_availability_approach.value == 'beta_distribution_function':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        l, r = st.columns(2)

        # with l:
        parameter = params.beta_method ## Conditional requirement
        if params.link_availability_approach.value == 'beta_distribution_function':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.highest_zone_number ## Essential parameter
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, min_value=0, step=1, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with r:
        parameter = params.resil_mitigation_approach
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.exposure_field  ## Essential parameter
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

    # ===================
    # RECOVERY VALUES
    # ===================

    element_number = 0
    section_number += 1
    st.header(f"{section_number}. Recovery", divider="orange")
    with st.expander("Recovery stages, duration, exposure-damage approach, and repairs"):
        l, r = st.columns(2)
        
        # with l:
        parameter = params.num_recovery_stages
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, min_value=1, step=1, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with r:
        parameter = params.num_duration_cases
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, min_value=1, step=1, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with r:
            
        # with ll:
        parameter = params.min_duration
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, min_value=0, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.max_duration
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, min_value=0, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)



        l, m, r = st.columns(3)

        # with m:
        parameter = params.hazard_recov_type
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with l:
        max = 10000000000.00
        if params.hazard_recov_type.value == 'percent':
            max = 100.00
        parameter = params.hazard_recov_length
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, max_value=max, min_value=0.00, step=0.01, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with r:
        parameter = params.hazard_recov_path_model
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.pills(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # l, r = st.columns(2)

        # with l:
        parameter = params.exposure_damage_approach
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.exposure_unit ## Conditional requirement
        if params.link_availability_approach.value == 'default_flood_exposure_function' or params.exposure_damage_approach.value == 'default_damage_table':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.exposure_damage_csv ## Conditional requirement
        if params.exposure_damage_approach.value == 'manual_bins' or params.exposure_damage_approach.value == 'manual_linear':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with r:
        parameter = params.repair_cost_approach
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.repair_network_type ## Conditional requirement
        if params.repair_cost_approach.value == 'default':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.pills(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.repair_cost_csv ## Conditional requirement
        if params.repair_cost_approach.value == 'user-defined':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.repair_time_approach
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.repair_time_csv ## Conditional requirement
        if params.repair_time_approach.value == 'user-defined':
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

    # ===================
    # ANALYSIS VALUES
    # ===================

    element_number = 0
    section_number += 1
    st.header(f"{section_number}. Analysis", divider="blue")
    with st.expander("Economics, vehicle occupancy, maintenance & redeployment, and costs"):
        l, r = st.columns(2)
        # with l:
        parameter = params.roi_analysis_type
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.discount_factor
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.vehicle_occupancy_car
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.vehicle_occupancy_bus ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.vehicle_occupancy_light_rail ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.vehicle_occupancy_heavy_rail ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.vot_per_hour
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.safety_cost
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.noise_cost
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.non_co2_cost
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # parameter = params.co2_cost
        # element_number += 1
        # display = ut.create_display_name(parameter, section=section_number, element=element_number)
        # st.number_input(display, value=parameter.value, key=parameter.name)
        # parameter.value = st.session_state[parameter.name]
        # ut.create_display_echo(parameter)

        # with r:
        parameter = params.dollar_year
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, min_value=1900, max_value=3000, step=1, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # parameter = params.co2_discount_factor
        # element_number += 1
        # display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        # st.number_input(display, value=parameter.value, key=parameter.name)
        # parameter.value = st.session_state[parameter.name]
        # ut.create_display_echo(parameter)

        parameter = params.veh_oper_cost_car
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.veh_oper_cost_bus ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.veh_oper_cost_light_rail ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.veh_oper_cost_heavy_rail ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.vot_wait_per_hour ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.safety_cost_bus ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.noise_cost_bus ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.non_co2_cost_bus ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # parameter = params.co2_cost_bus ## Conditional requirement
        # if params.calc_transit_metrics.value == 1:
        #     parameter.required = True
        # element_number += 1
        # display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        # st.number_input(display, value=parameter.value, key=parameter.name)
        # parameter.value = st.session_state[parameter.name]
        # ut.create_display_echo(parameter)

        l, ll, r= st.columns([2, 1, 1], vertical_alignment="bottom")
        # with l:
        parameter = params.transit_fare ## Conditional requirement
        if params.calc_transit_metrics.value == 1:
            parameter.required = True
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.number_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with ll:
        parameter = params.maintenance
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        # with r:
        parameter = params.redeployment
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.segmented_control(display, options=parameter.options, default=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

        parameter = params.crs
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

    # st.button("Next step ->", type="primary", on_click=) # check example 4 here https://docs.streamlit.io/develop/api-reference/layout/st.tabs
        
    # ===================
    # PYTHON AND RDRENV
    # ===================
    element_number = 0
    section_number += 1
    st.header(f"{section_number}. Python", divider="violet")
    with st.expander("Python installation location, Scripts location, and RDR main run file"):
        #======================================================================================================
        parameter = params.python
        forced_default = sys.executable

        if parameter.value is not None and parameter.value != "":
            st.session_state[parameter.name] = parameter.value
        if parameter.value is None or parameter.value == "":
            parameter.value = forced_default
        parameter_entry_disabled = True
        if st.button(f"Edit {parameter.title} (Not Recommended)", width='stretch', type='primary'):
            parameter_entry_disabled = not parameter_entry_disabled
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, disabled=parameter_entry_disabled, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)
        #======================================================================================================
        parameter = params.script
        forced_default = os.path.dirname(os.path.dirname(os.path.dirname(params.python.value))) + '\Scripts'

        if parameter.value is not None and parameter.value != "":
            st.session_state[parameter.name] = parameter.value
        if parameter.value is None or parameter.value == "":
            parameter.value = forced_default
        parameter_entry_disabled = True
        if st.button(f"Edit {parameter.title} (Not Recommended)", width='stretch', type='primary'):
            parameter_entry_disabled = not parameter_entry_disabled
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, disabled=parameter_entry_disabled, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)
        #======================================================================================================
        parameter = params.rdr       
        parameter_entry_disabled = True
        
        if st.button(f"Edit {parameter.title} (Not Recommended)", width='stretch', type='primary'):
            parameter_entry_disabled = not parameter_entry_disabled
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, disabled=parameter_entry_disabled, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)

if __name__ == "__main__":
    main()