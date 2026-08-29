// Run this only in a separate, empty Neo4j instance used for presentation.
CREATE CONSTRAINT demo_candidate_name IF NOT EXISTS FOR (n:Candidate) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT demo_skill_name IF NOT EXISTS FOR (n:Skill) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT demo_company_name IF NOT EXISTS FOR (n:Company) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT demo_institution_name IF NOT EXISTS FOR (n:Institution) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT demo_project_name IF NOT EXISTS FOR (n:Project) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT demo_technology_name IF NOT EXISTS FOR (n:Technology) REQUIRE n.name IS UNIQUE;

CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///demo_candidates.csv' AS row
  MERGE (c:Candidate {name: row.name})
  SET c.email = row.email, c.phone = row.phone, c.location = row.location,
      c.linkedin = row.linkedin, c.source_file = row.source_file
  RETURN count(*) AS candidates
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///demo_skills.csv' AS row
  MATCH (c:Candidate {name: row.candidate_name})
  MERGE (s:Skill {name: row.name})
  MERGE (c)-[r:HAS_SKILL]->(s)
  SET r.category = row.category
  RETURN count(*) AS skills
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///demo_experience.csv' AS row
  MATCH (c:Candidate {name: row.candidate_name})
  MERGE (e:Experience {
    job_title: row.job_title, company: row.company,
    start_date: coalesce(row.start_date, ''), end_date: coalesce(row.end_date, '')
  })
  SET e.location = row.location, e.description = row.description
  MERGE (company:Company {name: row.company})
  MERGE (c)-[:HAS_EXPERIENCE]->(e)
  MERGE (e)-[:AT_COMPANY]->(company)
  RETURN count(*) AS experiences
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///demo_education.csv' AS row
  MATCH (c:Candidate {name: row.candidate_name})
  MERGE (i:Institution {name: row.institution})
  MERGE (c)-[r:STUDIED_AT]->(i)
  SET r.degree = row.degree, r.location = row.location, r.date = row.date
  RETURN count(*) AS education
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///demo_projects.csv' AS row
  MATCH (c:Candidate {name: row.candidate_name})
  MERGE (p:Project {name: row.name})
  SET p.description = row.description, p.url = row.url
  MERGE (c)-[:WORKED_ON]->(p)
  RETURN count(*) AS projects
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///demo_technologies.csv' AS row
  MATCH (p:Project {name: row.project_name})
  MERGE (t:Technology {name: row.name})
  MERGE (p)-[:USES]->(t)
  RETURN count(*) AS technologies
}
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///demo_certifications.csv' AS row
  MATCH (c:Candidate {name: row.candidate_name})
  MERGE (x:Certification {name: row.name, issuer: coalesce(row.issuer, '')})
  SET x.date = row.date
  MERGE (c)-[:HAS_CERTIFICATION]->(x)
  RETURN count(*) AS certifications
}
RETURN candidates, skills, experiences, education, projects, technologies, certifications;
