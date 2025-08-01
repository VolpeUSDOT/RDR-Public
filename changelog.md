# RDR Changelog

## v2025_1

The RDR 2025.1 public release includes updates related to trip demand input files, the AequilibraE core model, and default parameter values for the resilience return on investment (ROI) module. Starting with the 2025.1 release, users are able to provide trip tables for an RDR analysis in either Open Matrix (OMX) or comma-separated values (CSV) format. The version of AequilibraE used by the RDR Tool Suite has been updated from 1.0.0 to 1.4.2 to include the latest performance improvements and bug fixes. The RDR Metamodel has been updated to work with the new version of AequilibraE more efficiently. Finally, default values in the ROI module have been updated to align with the latest USDOT BCA guidance from May 2025.

See documentation files for additional details.

## v2024_2_1

The RDR 2024.2.1 public release includes a revision to the Benefits Analysis Tool, specifically the TAZ Attribute Overlay tool, that enables the user to overlay geographic attributes onto their TAZs. This tool provides a generalized overlay functionality and can apply any attribute to TAZs; therefore it has been renamed to more accurately represent its functionality.

The previous example/default approach applying disadvantaged community metrics has been replaced with an example/default showing the application of census tract level poverty metrics.

## v2024_2

The RDR 2024.2 public release includes updates across the entire tool suite, primarily focused on use of publicly available data to generate an RDR analysis. The documentation has been expanded to include public data workflows as well as a new Reference Scenario based on the 2022 Ferndale earthquake. Updated visualizations, particularly in the Tableau workbook, provide better insight into where and under what scenarios benefits are found. Several highlights of the release are detailed below.

**RDR Metamodel**

- Reformatted the Model Parameters input file and eliminated the User Inputs input file to improve usability and clarity of how to define the scenario space.
- Added two new user parameters to control convergence criteria for the core model (AequilibraE user equilibrium routing): maximum gap and maximum number of iterations.
- Fixed a bug in the regression module that was assigning core model run outputs to the incorrect resilience projects.

**RDR ROI Analysis Tool**

- Updated methodology for the resilience return on investment (ROI) module for monetization of trips lost/gained and calculation of safety, noise, and emissions benefits.
- Corrected a bug in the benefits calculation related to associating network performance metric savings with project benefits.
- Developed a new Map dashboard in the Tableau workbook for visualizing the user's resilience projects geospatially. The map allows users to dynamically explore their project outcomes and symbolize network links by average exposure, project cost, and regret ranking.
- Refactored ROI module for readability and efficiency.
- Refreshed Tableau workbook with clearer text and resolved visualization bugs.

**RDR Benefits Analysis Tool**

- Renamed tool to emphasize its focus on understanding the distribution of benefits across users of the transportation network.
- Improved usability of the TAZ metrics HTML report by adding toggle on charts so users can switch between showing data for (a) all TAZ/TAZ pairs versus (b) only the subset of TAZ/TAZ pairs that would be impacted by the disruption.
- Refactored the benefits overlay tool to rely on geospatial processing via geopandas instead of arcpy, meaning that an ArcGIS license is no longer needed to run the tool.
- Updated default layer for the overlay component to use data from the Council on Environmental Quality (CEQ) Climate and Economic Justice Screening Tool (CEJST) in lieu of the prior default data from the Department of Transportation (DOT) Equitable Transportation Community Explorer.

**Public Data**

- Documented publicly available datasets and general workflows in the User Guide and Reference Scenario Library for developing:
  - Road and transit networks,
  - Trip tables,
  - Hazard impacts.
- Added helper tools demonstrating various public data workflows, including (a) creation of a road network from OpenStreetMap data, (b) implementation of a gravity model to translate production-attractions to origin-destination trips, (c) overlay of historical earthquake data on a real-world network to calculate link-level capacity and damage impacts.
- Created a new Reference Scenario to demonstrate the above public data workflows based on the 2022 Ferndale earthquake.

**Helper Tools**

- Added new functionality to the RDR User Interface:
  - Updated the order that parameters are set to prioritize those essential to running RDR.
  - Added more input validation to improve usability.
  - Updated scenario input validation helper tool to produce a CSV output that allows the user to review summary statistics on certain fields in the node and link files to check their reasonableness.
- Built in more user flexibility for the suite of Format Demand helper tools.
- Deprecated the GMNS_link_conversion Excel helper tool.

**Other Updates**

- Rebuilt the RDR conda environment, which now includes geopandas and osm2gmns.
- Updated default values in the ROI module to align with the latest USDOT BCA guidance from November 2024.
- Updated default repair cost values to align with the latest FHWA data.
- Converted all dollar values to 2023 dollars.

See documentation files for additional details.

## v2024_1

The RDR 2024.1 public release includes updates across the entire tool suite, primarily focused on improved user experience. The documentation has been updated to provide ease of access with a new RDR Quick Start Guide documenting installation and how to run a first RDR scenario. A new Reference Scenario Library has been added to provide the user with a fuller list of RDR example scenarios, including a new scenario focused on earthquake hazards and additional support for preparing a transit network for use in RDR.

**RDR Metamodel**

- Updated to AequilibraE version 1.0.0, a breaking AequilibraE update not backwards compatible with the version of AequilibraE (0.9.2) used by RDR 2023.2.
- Added new core model run outputs for validation and visualization, including a set of GeoJSON files to import into GIS software for visualization of network nodes and links.
- Streamlined the process for using existing core model runs in a new RDR run.

**RDR ROI Analysis Tool**

- Revamped the Tableau workbook output by the ROI Analysis Tool to include dashboards for benefit-cost analysis, regret analysis, and parameter settings used by the RDR run. The new dashboards provide additional views into the analysis results and provide the user better documentation of what assumptions were made.
- Reworked methodology for calculating emissions benefits to align with calculations for safety and noise benefits.

**RDR Exposure Analysis Tool**

- Added logging functionality for better user experience.
- Created a new 'Facility Type Manual' method for applying different exposure-disruption relationships for different asset types.
- Aligned tool with rest of RDR Tool Suite in referring to nodes as from_node_id and to_node_id.

**RDR Benefits Analysis Tool**

- Renamed tool to emphasize its full functionality.
- Refreshed the TAZ metrics HTML report to provide more narrative context and update color scheme.
- Edited configuration file to provide more flexibility in user-defined inputs and their file locations.
- Created a Reference Scenario showcasing how to run the tool for a sample analysis with the Sioux Falls model network.

**Helper Tools**

- Created the RDR User Interface, a command-line interface to guide users through the steps of setting up a run of the RDR Metamodel and ROI Analysis Tool. The User Interface helps users:
  - Set RDR configuration parameters,
  - Define the scenario space for an RDR run,
  - Save and load a configuration file in JSON format,
  - Generate an RDR batch file, which can be used to execute an RDR run.
- Created a Baseline Network Run helper tool to help the user validate the AequilibraE core model against their travel demand model. The tool runs the core model with no hazard scenario and no resilience projects to generate baseline network performance metrics that the user can compare at a high level against network performance data in their region of interest.
- Updated scenario input validation helper tool to match changes for the RDR 2024.1 public release.

**Other Updates**

- Updated default values for monetization of safety, noise, and emissions benefits and transit-specific BCA monetization values including cost per vehicle-mile from the FTA's National Transit Database 2022 metrics.
- Added logging functionality to the setup module to provide the user with errors associated with their configuration file.
- Reorganized and streamlined the configuration and batch files used by the RDR Tool Suite.

See documentation files for additional details.

## v2023_2

The RDR 2023.2 public release includes updates across the entire tool suite related to core model performance improvements, transit cost-benefit methodology, user input validation, TAZ metric analyses, and helper tools for processing transit and demand data. The following changes have been made:

**RDR Metamodel**

- Updated to AequilibraE version 0.9.2, a breaking AequilibraE update not backwards compatible with the version of AequilibraE (0.6.2) used by RDR 2023.1.
- Improved runtime and storage of the core model. The new version of AequilibraE brought significant runtime improvements. RDR disk space requirements were reduced via the removal of several large intermediate matrix files that were used only for debugging.
- Minor bug fixes to regression module to provide a fallback behavior to simple linear regression models if multitarget regression is not possible due to singularity of fit.
- Broke out depth-damage relationship and repair costs/times by asset type (e.g., highway, bridge, transit) based on review of existing literature.

**RDR ROI Analysis Module**

- Addressed transit-specific benefits and costs by integrating these costs into the ROI calculation by mode of transport. Transit-related costs include transit waiting time, lost transit fares, and incorporation of mode-specific vehicle operating costs.
- Added noise benefits/disbenefits for associated VMT changes due to detouring using the US DOT BCA guidance external highway cost values. Safety benefit/disbenefits calculations now use the US DOT BCA guidance external highway cost values. The emissions benefits/disbenefits use emissions per mile rates from EPA's MOVES model and monetary values from the US DOT BCA guidance.
- Added CO2-specific discount factor of 3 percent to reflect existing US DOT BCA guidance.
- Added an optional redeployment cost and an optional annual maintenance cost to project cost user inputs if future costs differ from the initial costs.
- Updated Tableau template to incorporate above changes so that additional benefit categories are incorporated into the BCA net benefits.

**RDR Benefits Analysis Tool**

- Changed methodology to group and show metrics based on TAZ of origin (rather than TAZ pair (origin-destination pair)).
- Changed the metrics of interest from 'trips,' 'miles,' and 'hours' to 'trips,' 'minutes per trip,' and 'miles per trip.' While this deviates from the main RDR Tool Suite, it provides results that are easier for the user to interpret in the context of the Benefits Analysis Tool.
- Made the tool more flexible to accommodate user-supplied variables that are continuous, in addition to the existing functionality to accept and analyze categorical variables. The tool automatically determines whether to treat the user-supplied data as continuous or categorical based on the number of unique values.
- Updated HTML report to include enhanced charts (e.g., more informative hover boxes) and statistical analyses with corresponding narrative.
- Added CSV outputs with summary table data so that users can access and analyze the underlying data results with their own analytical tools of choice.
- Integrated data for 0-car households (where applicable based on user inputs).
- Incorporated updates for input validation and usability.

**Helper tools**

- Significantly reworked suite of helper tools for converting GTFS files for modeling of transit within the RDR Tool Suite.
  - Added input validation and improved usability of helper tool suite to provide users with more clear error messaging.
  - Streamlined the workflow for taking GTFS transit feed data and converting it to (1) node and link CSV files compatible with RDR, (2) a transit GIS network compatible with the Exposure Analysis Tool.
  - Incorporated new geoprocessing tool to convert GTFS shapes for routes to a geodatabase compatible with RDR Exposure Analysis Tool. The third-party GTFS2GMNS tool does not make use of transit shape information that comes from the GTFS file shapes.txt. Its transit routes are straight lines between transit stops. The new geoprocessing tool provides higher geospatial fidelity on the transit routes, important for exposure analysis.
- Updated helper tools for creating and reviewing OMX demand files. The Format Demand helper tools provide scripts to help users construct OMX trip tables and view existing OMX files.
- Updated scenario input validation helper tool to match changes for the RDR 2023.2 public release.

**Default data**

- Refreshed RDR's set of default facility types to align with FHWA's road functional classes and GTFS route classifications. Explicit categories for transit boarding, transfer, and deboarding links allow for mode-specific benefit-cost analysis.
- Provided default values for bridge and transit depth-damage relationships, transit repair costs, and transit repair times.
- Added default values for transit-specific BCA monetization values including cost per vehicle-mile from the FTA's National Transit Database 2021 metrics.

See documentation files for additional details.

## v2023_1

The RDR 2023.1 public release includes updates related to transit modeling, incorporation of multiple trip tables, user benefits analysis, metamodel enhancements, expanded ROI analysis and reporting capabilities, and other minor bug fixes. The following changes have been made:

- Implements a transit network specification to allow for RDR scenarios to include transit trips in the analysis. The new specification aligns with the General Modeling Network Specification (GMNS) and can be constructed from the General Transit Feed Specification (GTFS) through a series of helper tools. The new specification is accompanied by user guidance, a new quick start example, and helper tools for construction and verification of the required RDR input files; see documentation for technical details.
- Adds the ability to run RDR scenarios with two separate trip tables--one for households owning vehicles and one for households without vehicles. The 'matrix' and 'nocar' trip tables should be contained in the same OMX file for input to the RDR Tool Suite. Separate trip tables allows for more nuanced modeling of network routing (e.g., interaction with transit, TNCs) and will be incorporated into the user benefits analysis in a future release.
- Includes a beta version of the RDR Benefits Analysis Tool. The standalone suite of user benefits analysis tools includes an ArcGIS-based overlay tool for intersecting TAZs with categorical overlays (e.g., Justice40 Transportation Disadvantaged Census Tracts) and a TAZ metrics tool for disaggregating resilience project benefits across categories of TAZs.
- Updates the RDR Metamodel to use the multitarget regression model as the default. Validation testing across several sample sizes and scenario space structures has shown the 'multitarget' approach to perform best out of all available RDR Metamodel approaches.
- Expands the RDR ROI Analysis Module to include tracking of safety (e.g., crash rates per vehicle-miles traveled) and emissions (e.g., CO2, NOx, SO2, PM2.5) benefits associated with the change in VMT from the resilience project investment. The ROI Analysis Module also requires users to specify the type of ROI analysis they wish to run (BCA, Regret, Breakeven) and allows for specification of project lifespans and calculates project residual cost as a benefit.

See documentation files for additional details.
