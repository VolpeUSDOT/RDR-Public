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

use_lib <- ifelse(any(grepl("RDRenv", .libPaths())),
  .libPaths()[grepl("RDRenv", .libPaths())],
  .libPaths()
)

num_to_install <- sum(is.na(match(loadpacks, (.packages(all.available = TRUE, lib.loc = use_lib)))))

if (num_to_install == 1) {
  print(paste("Installing", num_to_install,
              "R package and dependencies, this one-time operation might take several minutes."))
}

if (num_to_install > 1) {
  print(paste("Installing", num_to_install,
              "R packages and dependencies, this one-time operation might take several minutes."))
}

completed_installs <- 0

for (i in loadpacks) {
  if (length(grep(i, (.packages(
    all.available = TRUE,
    lib.loc = use_lib
  )))) == 0) {
    print(paste("<<>> Installing R package", i, "in", use_lib, "<<>>"))

    suppressMessages(
      install.packages(i,
        dependencies = c("Depends", "Imports"),
        repos = "https://cloud.r-project.org/",
        type = "binary",
        lib = use_lib,
        quiet = TRUE,
        verbose = FALSE
      )
    )

    completed_installs <- completed_installs + 1
  }
}

if (completed_installs > 0) {
  cat("Successfully installed", completed_installs, "packages for R at", Sys.getenv("R_HOME"))
}

rm(i, loadpacks)
