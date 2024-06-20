# Resilience and Disaster Recovery (RDR) Tool Suite

## Description:
The RDR Tool Suite enables transportation agencies to assess transportation resilience return on investment (ROI) for specific transportation assets over a range of potential future conditions and hazard scenarios, which can then be used as a consideration in existing project prioritization processes. The tool suite utilizes established Robust Decision-Making concepts developed to build on current TDM analyses and address deeply uncertain future scenarios. The RDR Tool Suite was developed at the US Dept. of Transportation's Volpe National Transportation Systems Center in support of FHWA and the Office of the Secretary of Transportation. [Click here](https://github.com/VolpeUSDOT/RDR-Public/tree/main/documentation) to download the technical documentation, user guide, quick start tutorial, and scenario checklist, as well as a brief overview document.

## Installation and Usage:
The RDR Tool Suite is a Python based tool.

The RDR Exposure Analysis Tool is an ESRI ArcGIS Pro based tool.

Detailed installation and usage instructions are explained in the [RDR User Guide documentation](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_UserGuide_final.pdf). A [video tutorial](#installing-rdr) on how to install RDR is also available.
* Install the required dependencies (including ESRI ArcGIS Pro if using the RDR Exposure Analysis Tool).
* Clone or download the repository. [Click here to download the most recent release.](https://github.com/VolpeUSDOT/RDR-Public/archive/refs/tags/v2023.2.zip) Alternatively, the GitHub code repository is available here: [https://github.com/VolpeUSDOT/RDR-Public](https://github.com/VolpeUSDOT/RDR-Public). Unzip the contents into the following directory on your local machine: C:\GitHub\RDR. (Note: _On some systems the RDR directory may need to be renamed from RDR-Public-Master_.)
* The documentation and quick start scenario files are included with the code release.

### Using this code
The RDR Tool Suite runs in a custom Python environment built on conda and Python 3.7. The Python dependencies are detailed in [`environment.yml`](https://github.com/VolpeUSDOT/RDR-Public/blob/main/environment.yml). There are R components as well, which will install automatically to the R package library within the user's RDR conda environment when first running the Tool Suite. To set up the RDR conda environment, follow these steps based on [this reference](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file).

Open Anaconda Prompt. From the Anaconda Prompt terminal, navigate to the location where you cloned the RDR repository and run the following:

```
conda env create -f environment.yml
conda info --envs
```

You should see `RDRenv` show up as an available environment.

### Next steps
At this point, you can verify that RDR is fully functional by running one of the pre-built quick start scenarios. For detailed instructions, consult the [RDR Quick Start Tutorial](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_QuickStartTutorial_final.pdf). You can also follow along with the [video tutorial](#running-quick-start-1) for running the first Quick Start scenario. Alternatively, consult the [RDR User Guide](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_UserGuide_final.pdf) and [RDR Run Checklist](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_Checklist_final.pdf) for guidance on developing your own scenarios.

## Contributing:
Add bugs and feature requests to the Issues tab in the [RDR-Public GitHub repository](https://github.com/VolpeUSDOT/RDR-Public/issues) for the Volpe Development Team to triage.

## Video Series:

#### RDR Overview
{% include youtube.html id="uMu84BcEOJ8" %}
<br>
<br>

#### Installing RDR
{% include youtube.html id="DVLlfUF2EP8" %}
<br>
<br>

#### Running Quick Start 1
{% include youtube.html id="J3G2cRM2PJQ" %}
<br>
<br>

## Credits:
* Kristin C. Lewis, PhD (Volpe) <Kristin.Lewis@dot.gov>
* Jonathan Badgley (Volpe)
* Andrew Breck (Volpe)
* Juwon Drake (Volpe)
* Daniel Flynn, PhD (Volpe)
* Olivia Gillham (Volpe)
* Michelle Gilmore (Volpe)
* Alexander Oberg (Volpe)
* Tess Perrone (Volpe)
* Gretchen Reese (Volpe)
* Scott Smith, PhD (Volpe)
* Kevin Zhang, PhD (Volpe)

## Project Sponsors:
The development of the RDR Tool Suite that contributed to this public version was funded by the U.S. Federal Highway Administration under Interagency Agreement (IAA) 693JJ319N300014 under the supervision of Michael Culp of the FHWA Office of Natural Environment and by the U.S. Dept. of Transportation under IAA 693JK421NT800008 under the supervision of Shawn Johnson of the Office of Research, Development and Technology (OST-R). Any opinions, findings, conclusions, or recommendations expressed in this material are those of the authors and do not necessarily reflect the views of the FHWA or OST-R.

## Acknowledgements:
The RDR team thanks our beta testers and collaborators at the Hampton Roads Transportation Planning Organization, the Hampton Roads Planning District Commission, the Houston-Galveston Area Council, and the Hillsborough Transportation Planning Organization, as well as Virginia DOT and Florida DOT, for their input during development.

## License:
This project is licensed under the terms of the [RDR End User License Agreement](https://github.com/VolpeUSDOT/RDR-Public/blob/main/LICENSE). Please read it carefully.
