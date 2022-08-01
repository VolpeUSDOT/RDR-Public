# Wrapper to render rdr_Metamodel_Regression.Rmd
options(warn = -1)

if (!file.exists("rdr_Rutil.R")) {
  stop("Error: could not find rdr_Rutil.R file.")
}

source("rdr_Rutil.R")

suppressPackageStartupMessages(library(rmarkdown))

# See rdr_Metamodel.py for order of the arguments
args <- commandArgs(trailingOnly = TRUE)

input_dir <- args[1]
output_dir <- args[2]
run_id <- args[3]
method <- args[4]

render("rdr_Metamodel_Regression.Rmd",
  params = list(
    input_dir = input_dir,
    output_dir = output_dir,
    run_id = run_id,
    method = method
  ),
  quiet = TRUE
)
