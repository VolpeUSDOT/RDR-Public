<!-- working badge, for working branch -->

[![Python_package Status](https://github.com/VolpeUSDOT/RDR-Public/workflows/Python_package/badge.svg)](https://github.com/VolpeUSDOT/RDR-Public/actions)


# Resilience and Disaster Recovery (RDR) Tool Suite

## Description:
The RDR Tool Suite enables transportation agencies to assess transportation resilience return on investment (ROI) for specific transportation assets over a range of potential future conditions and hazard scenarios, which can then be used as a consideration in existing project prioritization processes. The tool suite utilizes established Robust Decision-Making concepts developed to build on current TDM analyses and address deeply uncertain future scenarios. The RDR Tool Suite was developed at the US Dept. of Transportation's Volpe National Transportation Systems Center in support of FHWA and the Office of the Secretary of Transportation.

## Installation and Usage:
The RDR Tool Suite is a Python based tool.

The RDR Exposure Analysis Tool is an ESRI ArcGIS Pro based tool.

Detailed installation and usage instructions are explained in the RDR User Guide documentation here: (**link tbd**)
* Clone or download the repository.
* Install the required dependencies (including ESRI ArcGIS Pro if using the RDR Exposure Analysis Tool).
* Download the documentation and scenario datasets (**link tbd**)

### Using this code
The Python dependencies are detailed in `environment.yml` (**link tbd**). This assumes you have an installation of Python 3.7 and conda. These steps follow [this reference](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file). There are R components as well, which will install to the user's default R library when first run.

From your Anaconda Prompt terminal, navigate to the location where you cloned this repository and run the following:

```
conda env create -f environment.yml
conda info --envs
```

You should see `RDRenv` show up as an available environment.

## Contributing:
Add bugs and feature requests to the Issues tab in the [RDR-Public GitHub repository](https://github.com/VolpeUSDOT/RDR-Public/issues) for the Volpe Development Team to triage.

## Credits:
* Kristin C. Lewis, PhD (Volpe) <Kristin.Lewis@dot.gov>
* Jonathan Badgley (Volpe)
* Daniel Flynn, PhD (Volpe)
* Olivia Gillham (Volpe)
* Michelle Gilmore (Volpe)
* Alexander Oberg (Volpe)
* Gretchen Reese (Volpe)
* Scott Smith, PhD (Volpe)
* Kevin Zhang, PhD (Volpe)

## Project Sponsors:
The development of the RDR Tool Suite that contributed to this public version was funded by the U.S. Federal Highway Administration under Interagency Agreement (IAA) 693JJ319N300014 under the supervision of Michael Culp of the FHWA Office of Natural Environment and by the U.S. Dept. of Transportation under IAA 693JK421NT800008 under the supervision of Shawn Johnson of the Office of Research, Development and Technology (OST-R). Any opinions, findings, conclusions, or recommendations expressed in this material are those of the authors and do not necessarily reflect the views of the FHWA or OST-R.

## Acknowledgements:
The RDR team thanks our beta testers and collaborators at the Hampton Roads Transportation Planning Organization, the Hampton Roads Planning District Commission, the Houston-Galveston Area Council, and the Hillsborough Transportation Planning Organization, as well as Virginia DOT and Florida DOT, for their input during development.

## License:
This project is licensed under the terms of the RDR End User License Agreement. Please read it carefully. (**to be developed**)
