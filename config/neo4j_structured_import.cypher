DROP CONSTRAINT graph_node_id IF EXISTS;
MATCH (n) DETACH DELETE n;
CREATE CONSTRAINT graph_id_candidate IF NOT EXISTS FOR (n:`Candidate`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_candidate.csv' AS row
  MERGE (n:`Candidate` {graph_id: row.graph_id})
  SET n.`candidate_id` = row.`candidate_id`, n.`email` = row.`email`, n.`headline` = row.`headline`, n.`linkedin` = row.`linkedin`, n.`location` = row.`location`, n.`name` = row.`name`, n.`phone` = row.`phone`, n.`portfolio` = row.`portfolio`, n.`summary` = row.`summary`
  RETURN count(*) AS n_candidate
};
CREATE CONSTRAINT graph_id_certification IF NOT EXISTS FOR (n:`Certification`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_certification.csv' AS row
  MERGE (n:`Certification` {graph_id: row.graph_id})
  SET n.`issuer` = row.`issuer`, n.`name` = row.`name`, n.`year` = row.`year`
  RETURN count(*) AS n_certification
};
CREATE CONSTRAINT graph_id_company IF NOT EXISTS FOR (n:`Company`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_company.csv' AS row
  MERGE (n:`Company` {graph_id: row.graph_id})
  SET n.`name` = row.`name`
  RETURN count(*) AS n_company
};
CREATE CONSTRAINT graph_id_degree IF NOT EXISTS FOR (n:`Degree`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_degree.csv' AS row
  MERGE (n:`Degree` {graph_id: row.graph_id})
  SET n.`name` = row.`name`
  RETURN count(*) AS n_degree
};
CREATE CONSTRAINT graph_id_image IF NOT EXISTS FOR (n:`Image`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_image.csv' AS row
  MERGE (n:`Image` {graph_id: row.graph_id})
  SET n.`bbox` = row.`bbox`, n.`block_id` = row.`block_id`, n.`caption` = row.`caption`, n.`context_block_ids` = row.`context_block_ids`, n.`document_id` = row.`document_id`, n.`file_name` = row.`file_name`, n.`file_path` = row.`file_path`, n.`height` = row.`height`, n.`height_px` = row.`height_px`, n.`image_id` = row.`image_id`, n.`kind` = row.`kind`, n.`mime_type` = row.`mime_type`, n.`nearby_text` = row.`nearby_text`, n.`page_id` = row.`page_id`, n.`page_number` = row.`page_number`, n.`reading_order` = row.`reading_order`, n.`relative_path` = row.`relative_path`, n.`section_id` = row.`section_id`, n.`section_title` = row.`section_title`, n.`sha256` = row.`sha256`, n.`source_file` = row.`source_file`, n.`source_page` = row.`source_page`, n.`text` = row.`text`, n.`type` = row.`type`, n.`width` = row.`width`, n.`width_px` = row.`width_px`
  RETURN count(*) AS n_image
};
CREATE CONSTRAINT graph_id_institution IF NOT EXISTS FOR (n:`Institution`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_institution.csv' AS row
  MERGE (n:`Institution` {graph_id: row.graph_id})
  SET n.`name` = row.`name`
  RETURN count(*) AS n_institution
};
CREATE CONSTRAINT graph_id_language IF NOT EXISTS FOR (n:`Language`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_language.csv' AS row
  MERGE (n:`Language` {graph_id: row.graph_id})
  SET n.`name` = row.`name`
  RETURN count(*) AS n_language
};
CREATE CONSTRAINT graph_id_page IF NOT EXISTS FOR (n:`Page`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_page.csv' AS row
  MERGE (n:`Page` {graph_id: row.graph_id})
  SET n.`height` = row.`height`, n.`page_id` = row.`page_id`, n.`page_number` = row.`page_number`, n.`raw_text` = row.`raw_text`, n.`width` = row.`width`
  RETURN count(*) AS n_page
};
CREATE CONSTRAINT graph_id_project IF NOT EXISTS FOR (n:`Project`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_project.csv' AS row
  MERGE (n:`Project` {graph_id: row.graph_id})
  SET n.`description` = row.`description`, n.`name` = row.`name`, n.`project_id` = row.`project_id`, n.`technologies` = row.`technologies`, n.`url` = row.`url`
  RETURN count(*) AS n_project
};
CREATE CONSTRAINT graph_id_resume IF NOT EXISTS FOR (n:`Resume`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_resume.csv' AS row
  MERGE (n:`Resume` {graph_id: row.graph_id})
  SET n.`document_id` = row.`document_id`, n.`ingested_at` = row.`ingested_at`, n.`page_count` = row.`page_count`, n.`parser_version` = row.`parser_version`, n.`pdf_metadata` = row.`pdf_metadata`, n.`source_file` = row.`source_file`, n.`source_path` = row.`source_path`, n.`source_sha256` = row.`source_sha256`
  RETURN count(*) AS n_resume
};
CREATE CONSTRAINT graph_id_role IF NOT EXISTS FOR (n:`Role`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_role.csv' AS row
  MERGE (n:`Role` {graph_id: row.graph_id})
  SET n.`name` = row.`name`
  RETURN count(*) AS n_role
};
CREATE CONSTRAINT graph_id_section IF NOT EXISTS FOR (n:`Section`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_section.csv' AS row
  MERGE (n:`Section` {graph_id: row.graph_id})
  SET n.`block_ids` = row.`block_ids`, n.`document_id` = row.`document_id`, n.`normalized_type` = row.`normalized_type`, n.`section_id` = row.`section_id`, n.`start_page` = row.`start_page`, n.`title` = row.`title`
  RETURN count(*) AS n_section
};
CREATE CONSTRAINT graph_id_skill IF NOT EXISTS FOR (n:`Skill`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_skill.csv' AS row
  MERGE (n:`Skill` {graph_id: row.graph_id})
  SET n.`name` = row.`name`
  RETURN count(*) AS n_skill
};
CREATE CONSTRAINT graph_id_table IF NOT EXISTS FOR (n:`Table`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_table.csv' AS row
  MERGE (n:`Table` {graph_id: row.graph_id})
  SET n.`bbox` = row.`bbox`, n.`block_id` = row.`block_id`, n.`caption` = row.`caption`, n.`context_block_ids` = row.`context_block_ids`, n.`document_id` = row.`document_id`, n.`nearby_text` = row.`nearby_text`, n.`page_id` = row.`page_id`, n.`page_number` = row.`page_number`, n.`reading_order` = row.`reading_order`, n.`rows` = row.`rows`, n.`section_id` = row.`section_id`, n.`section_title` = row.`section_title`, n.`source_file` = row.`source_file`, n.`table_id` = row.`table_id`, n.`text` = row.`text`, n.`type` = row.`type`
  RETURN count(*) AS n_table
};
CREATE CONSTRAINT graph_id_textblock IF NOT EXISTS FOR (n:`TextBlock`) REQUIRE n.graph_id IS UNIQUE;
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_nodes_textblock.csv' AS row
  MERGE (n:`TextBlock` {graph_id: row.graph_id})
  SET n.`bbox` = row.`bbox`, n.`block_id` = row.`block_id`, n.`bold` = row.`bold`, n.`context_block_ids` = row.`context_block_ids`, n.`document_id` = row.`document_id`, n.`font_names` = row.`font_names`, n.`font_size` = row.`font_size`, n.`page_id` = row.`page_id`, n.`page_number` = row.`page_number`, n.`reading_order` = row.`reading_order`, n.`section_id` = row.`section_id`, n.`section_title` = row.`section_title`, n.`source_file` = row.`source_file`, n.`text` = row.`text`, n.`type` = row.`type`
  RETURN count(*) AS n_textblock
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_built.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`BUILT` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_built
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_earned_certification.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`EARNED_CERTIFICATION` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_earned_certification
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_earned_degree.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`EARNED_DEGREE` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_earned_degree
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_extracted_from.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`EXTRACTED_FROM` {graph_id: row.rel_id}]->(b)
  SET r.`claim_id` = row.`claim_id`, r.`field` = row.`field`, r.`match_type` = row.`match_type`, r.`page_number` = row.`page_number`, r.`score` = row.`score`, r.`value` = row.`value`
  RETURN count(*) AS r_extracted_from
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_has_block.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`HAS_BLOCK` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_has_block
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_has_context.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`HAS_CONTEXT` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_has_context
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_has_image.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`HAS_IMAGE` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_has_image
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_has_page.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`HAS_PAGE` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_has_page
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_has_resume.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`HAS_RESUME` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_has_resume
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_has_section.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`HAS_SECTION` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_has_section
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_has_skill.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`HAS_SKILL` {graph_id: row.rel_id}]->(b)
  SET r.`category` = row.`category`
  RETURN count(*) AS r_has_skill
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_held_role.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`HELD_ROLE` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_held_role
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_next_block.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`NEXT_BLOCK` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_next_block
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_speaks.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`SPEAKS` {graph_id: row.rel_id}]->(b)
  SET r.`proficiency` = row.`proficiency`
  RETURN count(*) AS r_speaks
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_studied_at.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`STUDIED_AT` {graph_id: row.rel_id}]->(b)
  SET r.`education_id` = row.`education_id`, r.`graduation_year` = row.`graduation_year`, r.`location` = row.`location`
  RETURN count(*) AS r_studied_at
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_uses.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`USES` {graph_id: row.rel_id}]->(b)
  RETURN count(*) AS r_uses
};
CALL () {
  LOAD CSV WITH HEADERS FROM 'file:///graph_rels_worked_at.csv' AS row
  MATCH (a {graph_id: row.from_id})
  MATCH (b {graph_id: row.to_id})
  MERGE (a)-[r:`WORKED_AT` {graph_id: row.rel_id}]->(b)
  SET r.`company` = row.`company`, r.`description` = row.`description`, r.`end_date` = row.`end_date`, r.`experience_id` = row.`experience_id`, r.`job_title` = row.`job_title`, r.`location` = row.`location`, r.`start_date` = row.`start_date`
  RETURN count(*) AS r_worked_at
};
RETURN n_candidate, n_certification, n_company, n_degree, n_image, n_institution, n_language, n_page, n_project, n_resume, n_role, n_section, n_skill, n_table, n_textblock, r_built, r_earned_certification, r_earned_degree, r_extracted_from, r_has_block, r_has_context, r_has_image, r_has_page, r_has_resume, r_has_section, r_has_skill, r_held_role, r_next_block, r_speaks, r_studied_at, r_uses, r_worked_at;
