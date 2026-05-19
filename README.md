# job-hunter-kit

## Description

`job-hunter-kit` is a local-first toolkit for discovering, filtering, and organizing ML/Data/AI job opportunities.

The first goal is to support my own job search in Germany by making the job discovery process more structured, repeatable, and less time-consuming.


## Problem
Job applications are not just about finding job postings.  
For each role, I usually need to understand the job description, compare it with my background, decide whether it is worth applying to, and prepare application materials.

Common problems include:

- Job descriptions can be long, unclear, or written in German, so quick translation and summarization are often needed.
- It takes time to compare each role with my CV, skills, experience, visa situation, and location preferences.

- Cover letters often need to be customized for each company and role.
- Application decisions and reasoning can easily stay in my head instead of becoming reusable rules.

This project aims to make the job search workflow more structured, explicit, and easier to repeat.

## Scope

This project is designed as a personal job application toolkit.  
The workflow starts from collecting job postings, then filtering and prioritizing them, and finally supporting CV and cover letter preparation.

### Phase 1: Job Collection and Rule-Based Filtering

The first phase focuses on collecting job opportunities and creating a structured job list.

This phase includes:

- Automatically collecting job postings from selected job platforms
- Extracting useful job information from each posting
- Applying initial rule-based filters
- Generating a job opportunity list
- Defining configurable include and exclude rules

The configuration should support conditions such as:

- Target roles
- Keywords to include
- Keywords to exclude
- Locations
- Work mode
- Language requirements
- Company or platform source

The goal of this phase is to reduce manual job browsing and create a cleaner list of potentially relevant opportunities.

### Phase 2: CV Matching and Application Prioritization

The second phase focuses on comparing job postings with my CV and deciding which jobs are worth applying to.

This phase includes:

- Comparing job descriptions with my CV
- Identifying matched and missing skills
- Estimating role fit
- Deciding whether a job is worth applying to
- Ranking jobs by application priority

The goal of this phase is to help me spend time on better-fit roles instead of reviewing every job manually.

### Phase 3: CV, Cover Letter, and ATS Review Support

The third phase focuses on preparing better application materials.

This phase includes:

- Supporting CV customization for specific job descriptions
- Generating or improving cover letters
- Checking whether the final application materials match the job requirements
- Reviewing whether the CV is likely to pass ATS screening
- Suggesting final improvements before applying

The goal of this phase is to make each application more targeted, consistent, and efficient.

