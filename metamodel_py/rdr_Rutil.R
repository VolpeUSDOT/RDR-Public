# Get all necessary packages across data prep and analysis scripts
# Packages the RDR scripts require are listed here in alphabetical order.
loadpacks <- c(
  "dplyr",
  "DT",
  "knitr",
  "jsonlite",
  "lhs",
  "lme4",
  "mlegp",
  "nlme",
  "readxl",
  "rmarkdown",
  "sjPlot",
  "tibble",
  "tidyr",
  "tools"
)


# Look for the exact directory name "RDRenv" bordered by path separators
is_rdr_env <- grepl("[/\\\\]RDRenv[/\\\\]", .libPaths())

use_lib <- ifelse(any(is_rdr_env),
  .libPaths()[is_rdr_env][1],
  .libPaths()[1]
)

# Explicitly set library paths to avoid pulling in outdated packages from personal user libraries
# while preserving core R libraries (.Library).
# Tier 1: conda env site library (highest priority, where our environment.yml packages install)
# Tier 2: base R library (for core/recommended system packages)
.libPaths(unique(c(use_lib, .Library)))

# We rely on Conda to manage the environment accurately for most packages.
# mlegp is not available on conda-forge, so we install it from CRAN if missing.
missing_packages <- loadpacks[is.na(match(loadpacks, .packages(all.available = TRUE)))]

if ("mlegp" %in% missing_packages) {
  print(paste("<<>> Installing R package mlegp from CRAN in", use_lib, "<<>>"))
  suppressMessages(
    install.packages("mlegp",
      dependencies = c("Depends", "Imports"),
      repos = "https://cloud.r-project.org/",
      type = "binary",
      lib = use_lib,
      quiet = TRUE,
      verbose = FALSE
    )
  )
  # Remove mlegp from missing_packages check after installing
  missing_packages <- missing_packages[missing_packages != "mlegp"]
}

if (length(missing_packages) > 0) {
  stop(paste(
    "The following required R packages are missing from the conda environment:",
    paste(missing_packages, collapse = ", "),
    "\nPlease ensure you built the Anaconda environment correctly using environment.yml."
  ))
}

rm(i, loadpacks)
