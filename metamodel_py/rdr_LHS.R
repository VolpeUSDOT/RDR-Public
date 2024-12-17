# Latin hypercube sampling
# Arguments:
# 1. Input directory
# 2. Output directory
# 3. Run ID
# 4. Filepath to model parameters (XLSX or JSON)
# 5. N sample to target
# 6. Metamodel type
# 7. Seed (optional)

# Setup ----
options(warn = -1) # Suppress warnings

if (!file.exists("rdr_Rutil.R")) {
  stop("Error: could not find rdr_Rutil.R file.")
}

source("rdr_Rutil.R")

suppressPackageStartupMessages(library(lhs, lib.loc = use_lib))
suppressPackageStartupMessages(library(dplyr, lib.loc = use_lib, warn.conflicts = FALSE))
suppressPackageStartupMessages(library(tidyr, lib.loc = use_lib, warn.conflicts = FALSE))
suppressPackageStartupMessages(library(tibble, lib.loc = use_lib, warn.conflicts = FALSE))
suppressPackageStartupMessages(library(readxl, lib.loc = use_lib))
suppressPackageStartupMessages(library(jsonlite, lib.loc = use_lib))
suppressPackageStartupMessages(library(tools, lib.loc = use_lib))

# See rdr_LHS.py for order of the arguments
args <- commandArgs(trailingOnly = TRUE)

input_dir <- args[1]
output_dir <- args[2]
run_id <- args[3]
model_params_file <- args[4]

n_sample_target <- as.numeric(args[5]) # from cfg['lhs_sample_target']

# Model type to use
model_type <- args[6] # from cfg['metamodel_type']

# Check for prior LHS samples with same run_id
# Look for any file in the output directory that looks like:
# AequilibraE_LHS_Design_{run_id}_{numberofsamples}.csv
prior_lhs <- list.files(path=output_dir,
                        pattern=paste0("AequilibraE_LHS_Design_", run_id, "_", "\\d+", ".csv"))

# If there are any relevant results, compile them into one data frame called completed_lhs
# First initialize empty data frame to compile information on prior LHS samples with the same run_id
completed_lhs <- data.frame(socio=factor(),
                            projgroup=factor(),
                            elasticity = factor(),
                            hazard = factor(),
                            recovery = factor(),
                            resil = factor(),
                            ID = character(),
                            LHS_ID = character())

if (length(prior_lhs) > 0) {
  # For each file in prior_lhs, read in the contents and add its rows to the 
  # completed_lhs data frame. Keep only rows where the LHS_ID column is not NA,
  # meaning that the row was actually included in the prior sample.
  # Then use distinct() to eliminate redundant rows.
  for (i in prior_lhs) {
    df_i = read.csv(file.path(output_dir, i),
                    colClasses = c(
                      "socio" = "factor", "projgroup" = "factor", "hazard" = "factor",
                      "recovery" = "factor", "resil" = "factor")) %>%
      filter(!is.na(LHS_ID))
    completed_lhs <- rbind(completed_lhs, df_i) %>% distinct()
  }
}

# Set up predictors with the levels for each predictor ----

# Read inputs from Model_Parameters.xlsx or UI-generated JSON file
if (file_ext(model_params_file) == 'xlsx') {
  prgrps <- read_xlsx(model_params_file, sheet = "ProjectGroups", col_types = "text")
} else {
  cfg_json <- fromJSON(model_params_file)
  prgrps <- cfg_json$rep
  prgrps <- prgrps %>% rename("Project ID" = name, "Project Groups" = group)
}

names(prgrps) <- make.names(names(prgrps))
# Add 'no' resil case for each project group
prgrps <- prgrps %>%
  add_row(Project.Groups = unique(prgrps$Project.Groups), Project.ID = "no") %>%
  unite("projgroup_resil", Project.Groups:Project.ID, remove = FALSE)
prgrps$Project.Groups <- as.factor(prgrps$Project.Groups)
prgrps$Project.ID <- as.factor(prgrps$Project.ID)
prgrps$projgroup_resil <- as.factor(prgrps$projgroup_resil)

# Read inputs from full_combos_runID.csv
full_combos <- read.csv(file.path(output_dir, paste0("full_combos_", run_id, ".csv")),
  colClasses = c(
    "socio" = "factor", "projgroup" = "factor", "hazard" = "factor",
    "recovery" = "factor", "resil" = "factor"
  )
)

full_combos$elasticity <- as.factor(full_combos$elasticity)

# Filter the completed_lhs to full_combos to ensure that if scenario space has been reduced
# we aren't including previous runs which are actually out of the scenario space.
# This will remove any combos which are not in the current full_combos set.

if (length(prior_lhs) > 0) {
  completed_lhs <- completed_lhs[completed_lhs$ID %in% (
    with(full_combos, paste(socio, projgroup, resil, elasticity, hazard, recovery, sep = "_"))), ]
}

# Check that the runs specified in completed_lhs actually exist
# If they do NOT, remove them from completed_lhs data frame
stillthere <- logical(length(completed_lhs))
for (e in 1:nrow(completed_lhs)) {
  ifelse(dir.exists(file.path(output_dir, "aeq_runs", "disrupt", run_id,
                              paste0(completed_lhs[e, 'socio'],
                                     completed_lhs[e, 'projgroup'],
                                     "_",
                                     completed_lhs[e, 'resil'],
                                     "_",
                                     as.character(completed_lhs[e, 'elasticity'] * -10),
                                     "_",
                                     completed_lhs[e, 'hazard'],
                                     "_",
                                     completed_lhs[e, 'recovery']))),
         stillthere[e] <- TRUE,
         stillthere[e] <- FALSE
  )
}
completed_lhs <- completed_lhs[stillthere,]

# Now that we've finished using elasticity as a numeric to get the file path in the above check,
# convert elasticity into a factor for the remainder of the script.
completed_lhs$elasticity <- as.factor(completed_lhs$elasticity)
  
# Check as a first pass that full set of samples will cover each dimension of scenario space at a minimum
# NOTE: This is not entirely rigorous since completed_lhs may no longer have n_sample_target runs
socio <- unique(full_combos$socio)
if (n_sample_target < length(socio)) {
  stop("Error: LHS sample target parameters will not cover all possible socio levels.")
}

# Use combination of projgroup and resil as dimension in LHS to avoid dependence issue
# Also avoids issue if there are different #s of projects within each project group
prgrps <- prgrps %>% filter(Project.Groups %in% unique(full_combos$projgroup))
projgroup_resil <- unique(prgrps$projgroup_resil)
if (n_sample_target < length(projgroup_resil)) {
  stop("Error: LHS sample target parameters will not cover all possible projgroup-resil levels.")
}

elasticity <- unique(full_combos$elasticity)
if (n_sample_target < length(elasticity)) {
  stop("Error: LHS sample target parameters will not cover all possible elasticity levels.")
}

hazard <- unique(full_combos$hazard)
if (n_sample_target < length(hazard)) {
  stop("Error: LHS sample target parameters will not cover all possible hazard levels.")
}

recovery <- unique(full_combos$recovery)
if (n_sample_target < length(recovery)) {
  stop("Error: LHS sample target parameters will not cover all possible recovery levels.")
}

preds <- c(
  "socio",
  "projgroup_resil",
  "elasticity",
  "hazard",
  "recovery"
)


# LHS sampling ----

# n = number of samples
# k = number of parameters, as in how many individual levels we have

# Each column = 1 parameter
# The values are equally distributed across rows within a column

# For each predictor column, convert it into the appropriate category
# https://stats.stackexchange.com/questions/388963/latin-hypercube-sampling-with-categorical-variables

# One quirk of this method is it can generate duplicate combinations, because of the rounding
# Solution: use a while loop, check for duplicates, and replace those duplicates with some other combo
# An easier solution: take 50% more of the target initially, then only keep non-duplicates
# A limited while loop is applied to catch any missing sample levels

# Increase the max tries by the number of new sample targets
try_count <- 1
n_sample_new <- n_sample_target - nrow(completed_lhs)
max_tries <- ifelse(n_sample_new > 0, 15 * n_sample_new, 15)

# Start with pass flag as F, then will convert to T when all original levels are represented in LHS sample
pass <- FALSE

# Increase the growth factor (initially 1.5) for each subsequent pass through the loop
# This also gets incremented when doing additional runs to add more candidate samples
# This gives us a nice distribution in the sample space even when doing additional runs

while (try_count <= max_tries && pass == FALSE) {

  # Sample growth factor
  sample_growth <- 1.5 + (try_count - 1) / 8

  # If a seed has been set in the config file, use this to set the RNG seed
  if (length(args) > 6) {
    set.seed(seed = args[7])
  }
  r1 <- as.data.frame(randomLHS(n = floor(n_sample_target * sample_growth), k = length(preds)))

  for (i in 1:ncol(r1)) {
    # Identify the predictor for assignment
    nlev <- length(get(preds[i]))
    r1[, i] <- floor(r1[, i] * nlev) + 1
    names(r1)[i] <- preds[i]
  }

  # Check for even distribution
  # apply(r1, 2, table)

  # Convert into predictor level names
  r_named <- r1

  for (i in 1:ncol(r_named)) {
    r_named[, i] <- as.factor(r_named[, i])
    levels(r_named[, i]) <- levels(get(preds[i]))
  }

  # Check for even distribution
  # apply(r_named, 2, table)

  # Separate the projgroup_resil column into projgroup and resil
  # Make ID columns
  r_named <- suppressMessages(r_named %>%
    left_join(prgrps) %>%
    rename(projgroup = Project.Groups, resil = Project.ID) %>%
    mutate(
      projgroup_resil = NULL,
      LHS_ID = paste(socio, projgroup, resil, elasticity, hazard, recovery, sep = "_")
    ))

  # Reduce down to the LHS sample target by removing duplicates, then sampling down at random
  # NOTE: This filtering method can result in sampling out a level of a factor
  r_named <- r_named %>%
    filter(!duplicated(LHS_ID))

  # If previous AequilibraE runs have been completed, remove them from the candidate pool as well
  if (length(prior_lhs) > 0) {
    r_named <- r_named %>%
      filter(!LHS_ID %in% completed_lhs$LHS_ID)
  }

  # If the number of possible new samples plus the number of prior samples is less than
  # the user's total number of desired samples, increment the try count and go directly back to 
  # the beginning of while loop to get more samples with a larger n.
  if (nrow(r_named) + nrow(completed_lhs) < n_sample_target) {
      try_count <- try_count + 1
      next
  }

  # Set seed before randomly selecting rows again
  if (length(args) > 6) {
    set.seed(seed = args[7])
  }

  if(nrow(completed_lhs) >= n_sample_target) {
    # If there are more than enough completed runs then we can just randomly select from
    # the completed runs instead of doing new runs.
    r_named <- completed_lhs %>%
      slice_sample(n = n_sample_target, replace = FALSE)
  } else {
    # Otherwise, randomly select the number of new samples, which when added to the existing runs,
    # will fulfill the user's desired sample size.
    r_named <- r_named %>%
      slice_sample(n = n_sample_target - nrow(completed_lhs), replace = FALSE)
    # If there are prior completed runs, concatenate completed runs with new runs
    if (length(prior_lhs) > 0) {
      r_named <- rbind(r_named, completed_lhs %>% select(-ID))
    }
  }

  # Check coverage of sample
  # Sufficient for 'base', 'multitarget'
  sample_level_n <- r_named %>%
    summarize_all(list(function(x) length(unique(x)))) %>%
    t() %>%
    as.data.frame() %>%
    rownames_to_column(var = "preds") %>%
    filter(!grepl("ID", preds))
  colnames(sample_level_n)[2] <- "sample"

  combo_level_n <- full_combos %>%
    summarize_all(list(function(x) length(unique(x)))) %>%
    t() %>%
    as.data.frame() %>%
    rownames_to_column(var = "preds") %>%
    filter(!grepl("ID", preds))
  colnames(combo_level_n)[2] <- "full"

  level_check <- suppressMessages(full_join(sample_level_n, combo_level_n) %>%
    mutate(pass = sample == full))

  if (model_type == "interact" || model_type == "ALL") {
    # Coverage check for hazard and recovery interaction if levels > 1

    # Coverage check for resil and projgroup if levels > 1
    r_named_projgroup_resil <- paste(r_named$projgroup, r_named$resil, sep = "_")
    projgroup_resil_pass <- length(unique(r_named_projgroup_resil)) == length(projgroup_resil)
    level_check <- level_check %>%
      add_row(
        preds = "projgroup_resil", sample = length(unique(r_named_projgroup_resil)),
        full = length(projgroup_resil), pass = projgroup_resil_pass
      )
  }

  if (model_type == "projgroupLM" || model_type == "mixedeffects" || model_type == "ALL") {
    # Check coverage for each project group subset

    # Coverage check for hazard and recovery interaction if levels > 1

    # Coverage check for 'no' baseline in each project group subset
  }

  try_count <- try_count + 1
  pass <- all(level_check$pass) # all must be true to pass
} # end limited while loop

# Check that LHS sample covers all levels of all factors
not_covered <- level_check %>% filter(pass == FALSE)
if (nrow(not_covered) > 0) {
  stop(paste(
    "Error: LHS samples do not cover all possible coverage tests. Coverage tests failed are:",
    paste0(paste(not_covered$preds, sep = ", "), "."),
    "Re-run lhs module, possibly with larger lhs_sample_target parameter."
  ))
}

full_combos <- suppressMessages(full_combos %>%
  mutate(ID = paste(socio, projgroup, resil, elasticity, hazard, recovery, sep = "_")) %>%
  left_join(r_named))

if (nrow(full_combos %>% filter(!is.na(LHS_ID))) < n_sample_target) {
  stop("Error: LHS module did not find enough lhs_sample_target core runs, please run module again.")
}

# Write output ----
write.csv(full_combos,
  file = file.path(
    output_dir,
    paste0(
      "AequilibraE_LHS_Design_", run_id, "_",
      n_sample_target, ".csv"
    )
  ),
  row.names = FALSE
)
