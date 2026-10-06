import os
import sys
import datetime
import pandas as pd
import numpy as np
import params
import streamlit as st

def main():
    st.set_page_config(page_title="RDR Help and Documentation", page_icon="C:\GitHub\RDR\gui\__siteIcon__ .ico")
    st.logo("C:\GitHub\RDR\gui\__siteIcon__ .ico")

    st.write("# Help and Documentation")

    st.markdown("""
                Installation instructions are provided in the [Quick Start Guide](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_GettingStarted_final.pdf), and more detailed usage instructions are provided in the [User Guide](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_UserGuide_final.pdf).

                - Download the latest release on the [Releases page](https://github.com/VolpeUSDOT/RDR-Public/releases).
                - Install the required dependencies.
                - The documentation, quick start, and reference scenario files are included with the code release.
                  - [Technical Document](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_TechnicalDocument_final.pdf)
                  - [User Guide](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_UserGuide_final.pdf)
                  - [Quick Start Guide](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_GettingStarted_final.pdf)
                  - [Run Checklist](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_Checklist_final.pdf)
                  - [Reference Scenario Library](https://github.com/VolpeUSDOT/RDR-Public/blob/main/documentation/RDR_ScenarioExamples_final.pdf)
                """)
    
if __name__ == "__main__":
    main()