-- Create a view for conversation extraction
-- Project ID: adnovum-gm-cai

CREATE OR REPLACE VIEW `adnovum-gm-cai.ds_iIVR_agent_export.conversation_extraction_view` AS
WITH conversation_turns AS (
  SELECT 
    `conversation:name` as full_session_id,
    turn_position,
    1 as message_order,
    'User' as role,
    JSON_VALUE(request, '$.queryInput.text.text') as message
  FROM `ds_iIVR_agent_export.ct_interaction_log`
  WHERE JSON_VALUE(request, '$.queryInput.text.text') IS NOT NULL
  
  UNION ALL
  
  SELECT 
    `conversation:name` as full_session_id,
    turn_position,
    2 as message_order,
    'Bot' as role,
    -- Handle initial greeting in responseMessages[1] and regular responses in [0]
    COALESCE(
      JSON_VALUE(response, '$.queryResult.responseMessages[1].text.text[0]'),
      JSON_VALUE(response, '$.queryResult.responseMessages[0].text.text[0]')
    ) as message
  FROM `ds_iIVR_agent_export.ct_interaction_log`
  WHERE COALESCE(
    JSON_VALUE(response, '$.queryResult.responseMessages[1].text.text[0]'),
    JSON_VALUE(response, '$.queryResult.responseMessages[0].text.text[0]')
  ) IS NOT NULL
)
SELECT 
  -- Extract project ID
  REGEXP_EXTRACT(full_session_id, r'projects/([^/]+)') as project_id,
  -- Extract agent ID
  REGEXP_EXTRACT(full_session_id, r'/agents/([^/]+)') as agent_id,
  -- Extract session ID (handle both formats: /sessions/ and /environments/-/sessions/)
  CASE 
    WHEN REGEXP_CONTAINS(full_session_id, r'/environments/-/sessions/') THEN
      REGEXP_EXTRACT(full_session_id, r'/environments/-/sessions/([^/]+)')
    ELSE
      REGEXP_EXTRACT(full_session_id, r'/sessions/([^/]+)')
  END as session_id,
  TO_JSON_STRING(
    ARRAY_AGG(
      STRUCT(role, message)
      ORDER BY turn_position, message_order
    )
  ) as conversation_turns
FROM conversation_turns
GROUP BY project_id, agent_id, session_id
ORDER BY project_id, agent_id, session_id;
