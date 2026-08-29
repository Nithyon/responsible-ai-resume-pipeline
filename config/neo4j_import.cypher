CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///resume_candidates.csv' AS row
  WITH row WHERE row.candidate_id IS NOT NULL AND trim(row.candidate_id) <> ''
    AND row.source_sha256 IS NOT NULL AND trim(row.source_sha256) <> ''
  MERGE (c:Candidate {candidate_id: row.candidate_id})
  SET c.name = row.name, c.email = row.email, c.phone = row.phone,
      c.location = row.location, c.linkedin = row.linkedin,
      c.portfolio = row.portfolio, c.headline = row.headline, c.summary = row.summary
  MERGE (r:Resume {source_sha256: row.source_sha256})
  SET r.source_file = row.source_file, r.ingested_at = row.ingested_at,
      r.parser_version = row.parser_version
  MERGE (c)-[:HAS_RESUME]->(r)
  RETURN count(*) AS candidates
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///resume_skills.csv' AS row
  WITH row WHERE row.name IS NOT NULL AND trim(row.name) <> ''
  MATCH (c:Candidate {candidate_id: row.candidate_id})
  MERGE (s:Skill {name: row.name})
  MERGE (c)-[r:HAS_SKILL]->(s)
  SET r.category = row.category
  RETURN count(*) AS skills
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///resume_experience.csv' AS row
  WITH row WHERE row.company IS NOT NULL AND trim(row.company) <> ''
    AND row.job_title IS NOT NULL AND trim(row.job_title) <> ''
  MATCH (c:Candidate {candidate_id: row.candidate_id})
  MERGE (company:Company {name: row.company})
  MERGE (c)-[r:WORKED_AT {experience_id: row.experience_id}]->(company)
  SET r.job_title = row.job_title, r.location = row.location,
      r.start_date = row.start_date, r.end_date = row.end_date,
      r.description = row.description
  MERGE (role:Role {name: row.job_title})
  MERGE (c)-[:HELD_ROLE]->(role)
  RETURN count(*) AS experiences
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///resume_education.csv' AS row
  WITH row WHERE row.institution IS NOT NULL AND trim(row.institution) <> ''
    AND row.degree IS NOT NULL AND trim(row.degree) <> ''
  MATCH (c:Candidate {candidate_id: row.candidate_id})
  MERGE (i:Institution {name: row.institution})
  MERGE (c)-[r:STUDIED_AT {education_id: row.education_id}]->(i)
  SET r.graduation_year = row.graduation_year, r.location = row.location
  MERGE (d:Degree {name: row.degree})
  MERGE (c)-[:EARNED_DEGREE]->(d)
  RETURN count(*) AS education
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///resume_projects.csv' AS row
  WITH row WHERE row.project_id IS NOT NULL AND trim(row.project_id) <> ''
  MATCH (c:Candidate {candidate_id: row.candidate_id})
  MERGE (p:Project {project_id: row.project_id})
  SET p.name = row.name, p.technologies = row.technologies,
      p.description = row.description, p.url = row.url
  MERGE (c)-[:BUILT]->(p)
  RETURN count(*) AS projects
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///resume_project_skills.csv' AS row
  WITH row WHERE row.technology IS NOT NULL AND trim(row.technology) <> ''
  MATCH (p:Project {project_id: row.project_id})
  MERGE (s:Skill {name: row.technology})
  MERGE (p)-[:USES]->(s)
  RETURN count(*) AS project_skills
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///resume_certifications.csv' AS row
  WITH row WHERE row.name IS NOT NULL AND trim(row.name) <> ''
    AND row.issuer IS NOT NULL AND trim(row.issuer) <> ''
  MATCH (c:Candidate {candidate_id: row.candidate_id})
  MERGE (x:Certification {name: row.name, issuer: row.issuer})
  SET x.year = row.year
  MERGE (c)-[:EARNED_CERTIFICATION]->(x)
  RETURN count(*) AS certifications
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///resume_languages.csv' AS row
  WITH row WHERE row.name IS NOT NULL AND trim(row.name) <> ''
  MATCH (c:Candidate {candidate_id: row.candidate_id})
  MERGE (l:Language {name: row.name})
  MERGE (c)-[r:SPEAKS]->(l)
  SET r.proficiency = row.proficiency
  RETURN count(*) AS languages
}
RETURN candidates, skills, experiences, education, projects,
       project_skills, certifications, languages;
