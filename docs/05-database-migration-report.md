# Database Migration Report

Date: 2026-09-09 15:41:17

## Tables Synced

| Table | Old rows | New rows | Status |
|-------|----------|----------|--------|
| `oc_users` | 23 | 23 | OK |
| `oc_accounts` | 23 | 23 | OK |
| `oc_accounts_data` | 345 | 345 | OK |
| `oc_preferences` | 1031 | 1031 | OK |
| `oc_authtoken` | 70 | 70 | OK |
| `oc_groups` | 3 | 3 | OK |
| `oc_group_user` | 23 | 23 | OK |
| `oc_group_admin` | 1 | 1 | OK |
| `oc_storages` | 25 | 25 | OK |
| `oc_mounts` | 62 | 62 | OK |
| `oc_share` | 38 | 38 | OK |
| `oc_filecache` | 32623 | 32623 | OK |
| `oc_activity` | 24812 | 24812 | OK |
| `oc_addressbooks` | 23 | 23 | OK |
| `oc_announcements` | 2 | 2 | OK |
| `oc_announcements_map` | 2 | 2 | OK |
| `oc_bruteforce_attempts` | 2 | 2 | OK |
| `oc_calendar_reminders` | 5 | 5 | OK |
| `oc_calendarobjects` | 13 | 13 | OK |
| `oc_calendarobjects_props` | 28 | 28 | OK |
| `oc_calendars` | 30 | 29 | MISMATCH |
| `oc_cards` | 25 | 25 | OK |
| `oc_circles_circle` | 30 | 30 | OK |
| `oc_circles_event` | 26 | 27 | MISMATCH |
| `oc_circles_member` | 55 | 55 | OK |
| `oc_circles_membership` | 52 | 53 | MISMATCH |
| `oc_collectives` | 3 | 3 | OK |
| `oc_collectives_p_versions` | 5 | 5 | OK |
| `oc_collectives_pages` | 3 | 3 | OK |
| `oc_collectives_s_docs` | 156 | 156 | OK |
| `oc_collectives_s_files` | 3 | 3 | OK |
| `oc_collectives_s_words` | 156 | 156 | OK |
| `oc_collectives_shares` | 1 | 1 | OK |
| `oc_comments` | 507 | 507 | OK |
| `oc_comments_read_markers` | 1 | 1 | OK |
| `oc_directlink` | 6 | 6 | OK |
| `oc_ex_apps_daemons` | 1 | 1 | OK |
| `oc_file_locks` | 16 | 16 | OK |
| `oc_filecache_extended` | 13416 | 13511 | MISMATCH |
| `oc_files_lock` | 4 | 4 | OK |
| `oc_files_metadata` | 10216 | 10218 | MISMATCH |
| `oc_files_metadata_index` | 10217 | 10227 | MISMATCH |
| `oc_files_trash` | 806 | 806 | OK |
| `oc_files_versions` | 13548 | 13550 | MISMATCH |
| `oc_flow_checks` | 3 | 3 | OK |
| `oc_flow_operations` | 2 | 2 | OK |
| `oc_flow_operations_scope` | 2 | 2 | OK |
| `oc_forms_v2_forms` | 4 | 4 | OK |
| `oc_forms_v2_shares` | 1 | 1 | OK |
| `oc_formulabase_colls` | 2 | 2 | OK |
| `oc_forum_bbcodes` | 3 | 3 | OK |
| `oc_forum_cat_headers` | 1 | 1 | OK |
| `oc_forum_categories` | 3 | 3 | OK |
| `oc_forum_category_perms` | 8 | 8 | OK |
| `oc_forum_drafts` | 2 | 2 | OK |
| `oc_forum_guest_sessions` | 2 | 2 | OK |
| `oc_forum_post_history` | 2 | 2 | OK |
| `oc_forum_posts` | 25 | 25 | OK |
| `oc_forum_reactions` | 3 | 3 | OK |
| `oc_forum_read_markers` | 38 | 38 | OK |
| `oc_forum_roles` | 4 | 4 | OK |
| `oc_forum_thread_subs` | 5 | 5 | OK |
| `oc_forum_threads` | 12 | 12 | OK |
| `oc_forum_user_roles` | 25 | 25 | OK |
| `oc_forum_users` | 23 | 23 | OK |
| `oc_job_classes_registry` | 152 | 160 | MISMATCH |
| `oc_job_runs` | 559741 | 565448 | MISMATCH |
| `oc_known_users` | 5 | 5 | OK |
| `oc_login_ips_aggregated` | 162 | 162 | OK |
| `oc_mail_accounts` | 20 | 20 | OK |
| `oc_mail_attachments` | 19 | 19 | OK |
| `oc_mail_coll_addresses` | 52 | 52 | OK |
| `oc_mail_local_messages` | 21 | 21 | OK |
| `oc_mail_mailboxes` | 100 | 100 | OK |
| `oc_mail_message_tags` | 317 | 317 | OK |
| `oc_mail_messages` | 9472 | 9472 | OK |
| `oc_mail_recipients` | 22834 | 22834 | OK |
| `oc_mail_tags` | 70 | 70 | OK |
| `oc_mail_trusted_senders` | 6 | 6 | OK |
| `oc_maps_address_geo` | 8 | 8 | OK |
| `oc_maps_photos` | 701 | 701 | OK |
| `oc_mimetypes` | 73 | 62 | MISMATCH |
| `oc_notes_meta` | 1 | 1 | OK |
| `oc_notifications` | 67 | 67 | OK |
| `oc_notifications_pushhash` | 16 | 16 | OK |
| `oc_notifications_settings` | 23 | 23 | OK |
| `oc_officeonline_wopi` | 50 | 50 | OK |
| `oc_onlyoffice_filekey` | 2649 | 2650 | MISMATCH |
| `oc_polls_polls` | 1 | 1 | OK |
| `oc_polls_preferences` | 6 | 6 | OK |
| `oc_previews` | 77844 | 77869 | MISMATCH |
| `oc_profile_config` | 18 | 18 | OK |
| `oc_ratelimit_entries` | 1 | 1 | OK |
| `oc_reactions` | 33 | 33 | OK |
| `oc_reader_bookmarks` | 10 | 10 | OK |
| `oc_reader_prefs` | 4 | 4 | OK |
| `oc_recent_contact` | 8 | 8 | OK |
| `oc_recognize_fs_moves` | 93 | 93 | OK |
| `oc_sketch_pk_recent` | 8 | 8 | OK |
| `oc_suspicious_login` | 1 | 1 | OK |
| `oc_suspicious_login_model` | 11 | 11 | OK |
| `oc_tables_columns` | 129 | 129 | OK |
| `oc_tables_row_cells_datetime` | 166 | 166 | OK |
| `oc_tables_row_cells_number` | 151 | 151 | OK |
| `oc_tables_row_cells_selection` | 713 | 713 | OK |
| `oc_tables_row_cells_text` | 843 | 843 | OK |
| `oc_tables_row_sleeves` | 352 | 352 | OK |
| `oc_tables_shares` | 20 | 20 | OK |
| `oc_tables_views` | 16 | 16 | OK |
| `oc_talk_attachments` | 4 | 4 | OK |
| `oc_talk_attendees` | 84 | 84 | OK |
| `oc_talk_bots_server` | 9 | 9 | OK |
| `oc_talk_conversation_tags` | 24 | 24 | OK |
| `oc_talk_rooms` | 73 | 73 | OK |
| `oc_talk_sessions` | 1 | 2 | MISMATCH |
| `oc_teamhub_audit_log` | 5 | 5 | OK |
| `oc_teamhub_integ_registry` | 4 | 4 | OK |
| `oc_teamhub_presence_types` | 5 | 5 | OK |
| `oc_teamhub_team_app_resources` | 3 | 3 | OK |
| `oc_text_documents` | 31 | 33 | MISMATCH |
| `oc_text_sessions` | 22 | 23 | MISMATCH |
| `oc_text_steps` | 212 | 214 | MISMATCH |
| `oc_twofactor_providers` | 65 | 65 | OK |
| `oc_user_status` | 24 | 24 | OK |
| `oc_duplicatefinder_dups` | 1024 | 1024 | OK |
| `oc_duplicatefinder_finfo` | 14018 | 14018 | OK |
| `oc_listman_list` | 1 | 1 | OK |
| `oc_listman_settings` | 7 | 7 | OK |
| `oc_preview_generation` | 42 | 42 | OK |
| `oc_user_saml_configurations` | 2 | 2 | OK |

## Skipped (272 tables)

- `oc_share_external`
- `oc_activity_mq`
- `oc_appconfig_ex`
- `oc_astrolabe_agent_conv`
- `oc_authorized_groups`
- `oc_calendar_appt_bookings`
- `oc_calendar_appt_configs`
- `oc_calendar_invitations`
- `oc_calendar_proposal_dats`
- `oc_calendar_proposal_dts`
- `oc_calendar_proposal_pts`
- `oc_calendar_proposal_vts`
- `oc_calendar_resources`
- `oc_calendar_resources_md`
- `oc_calendar_rooms`
- `oc_calendar_rooms_md`
- `oc_calendars_federated`
- `oc_calendarsubscriptions`
- `oc_circles_mount`
- `oc_circles_mountpoint`
- `oc_circles_remote`
- `oc_circles_share_lock`
- `oc_circles_token`
- `oc_collectives_page_links`
- `oc_collectives_page_trash`
- `oc_collectives_sessions`
- `oc_collectives_tags`
- `oc_collectives_u_settings`
- `oc_collres_accesscache`
- `oc_collres_collections`
- `oc_collres_resources`
- `oc_csb_log_entries`
- `oc_dav_absence`
- `oc_dav_cal_proxy`
- `oc_dav_shares`
- `oc_direct_edit`
- `oc_esignature_sessions`
- `oc_ex_apps`
- `oc_ex_apps_routes`
- `oc_ex_apps_talk_bots`
- `oc_ex_deploy_options`
- `oc_ex_occ_commands`
- `oc_ex_settings_forms`
- `oc_ex_task_processing`
- `oc_ex_ui_files_actions`
- `oc_ex_ui_scripts`
- `oc_ex_ui_states`
- `oc_ex_ui_styles`
- `oc_ex_ui_top_menu`
- `oc_external_applicable`
- `oc_external_config`
- `oc_external_mounts`
- `oc_external_options`
- `oc_federated_invites`
- `oc_federated_reshares`
- `oc_files_reminders`
- `oc_forms_v2_answers`
- `oc_forms_v2_options`
- `oc_forms_v2_questions`
- `oc_forms_v2_submissions`
- `oc_forms_v2_uploaded_files`
- `oc_formulabase_formulas`
- `oc_formulabase_history`
- `oc_formulabase_shares`
- `oc_forum_bookmarks`
- `oc_forum_templates`
- `oc_group_folders`
- `oc_group_folders_acl`
- `oc_group_folders_groups`
- `oc_group_folders_manage`
- `oc_group_folders_trash`
- `oc_group_folders_versions`
- `oc_ldap_group_mapping`
- `oc_ldap_group_membership`
- `oc_ldap_user_mapping`
- `oc_login_address`
- `oc_login_flow_v2`
- `oc_mail_action_step`
- `oc_mail_actions`
- `oc_mail_aliases`
- `oc_mail_blocks_shares`
- `oc_mail_cc_tasks`
- `oc_mail_delegations`
- `oc_mail_internal_address`
- `oc_mail_messages_retention`
- `oc_mail_messages_snoozed`
- `oc_mail_provisionings`
- `oc_mail_smime_certificates`
- `oc_mail_text_blocks`
- `oc_maps_apikeys`
- `oc_maps_device_points`
- `oc_maps_device_shares`
- `oc_maps_devices`
- `oc_maps_favorite_shares`
- `oc_maps_favorites`
- `oc_maps_tracks`
- `oc_notifications_webpush`
- `oc_oauth2_access_tokens`
- `oc_oauth2_clients`
- `oc_officeonline_locks`
- `oc_onlyoffice_instance`
- `oc_onlyoffice_permissions`
- `oc_open_local_editor`
- `oc_photos_albums`
- `oc_photos_albums_collabs`
- `oc_photos_albums_files`
- `oc_polls_comments`
- `oc_polls_groups`
- `oc_polls_groups_polls`
- `oc_polls_log`
- `oc_polls_notif`
- `oc_polls_options`
- `oc_polls_share`
- `oc_polls_votes`
- `oc_polls_watch`
- `oc_preferences_ex`
- `oc_preview_locations`
- `oc_preview_versions`
- `oc_privacy_admins`
- `oc_profile_fields_definitions`
- `oc_profile_fields_values`
- `oc_properties`
- `oc_recognize_face_clusters`
- `oc_recognize_face_detections`
- `oc_recognize_fs_access_updates`
- `oc_recognize_fs_creations`
- `oc_recognize_fs_deletions`
- `oc_recognize_queue_faces`
- `oc_recognize_queue_imagenet`
- `oc_recognize_queue_landmarks`
- `oc_recognize_queue_movinet`
- `oc_recognize_queue_musicnn`
- `oc_remote_signing_queues`
- `oc_retention`
- `oc_schedulingobjects`
- `oc_sec_signatory`
- `oc_shares_limits`
- `oc_storages_credentials`
- `oc_tables_contexts_context`
- `oc_tables_contexts_navigation`
- `oc_tables_contexts_page`
- `oc_tables_contexts_page_content`
- `oc_tables_contexts_rel_context_node`
- `oc_tables_favorites`
- `oc_tables_log`
- `oc_tables_row_cells_relation`
- `oc_tables_row_cells_usergroup`
- `oc_tables_rows`
- `oc_talk_bans`
- `oc_talk_bots_conversation`
- `oc_talk_bridges`
- `oc_talk_commands`
- `oc_talk_consent`
- `oc_talk_internalsignaling`
- `oc_talk_invitations`
- `oc_talk_phone_numbers`
- `oc_talk_poll_votes`
- `oc_talk_polls`
- `oc_talk_proxy_messages`
- `oc_talk_reminders`
- `oc_talk_retry_ocm`
- `oc_talk_scheduled_msg`
- `oc_talk_thread_attendees`
- `oc_talk_threads`
- `oc_taskprocessing_tasks`
- `oc_tcb_commands`
- `oc_teamhub_announce_read`
- `oc_teamhub_budget_lane`
- `oc_teamhub_budget_lane_editor`
- `oc_teamhub_buildings`
- `oc_teamhub_comments`
- `oc_teamhub_dec_audit`
- `oc_teamhub_dec_cat_apprs`
- `oc_teamhub_dec_categories`
- `oc_teamhub_dec_ext_links`
- `oc_teamhub_dec_links`
- `oc_teamhub_dec_meetings`
- `oc_teamhub_dec_tasks`
- `oc_teamhub_decision_audience`
- `oc_teamhub_decision_team`
- `oc_teamhub_decisions`
- `oc_teamhub_expense`
- `oc_teamhub_expiry_request`
- `oc_teamhub_floors`
- `oc_teamhub_holidays`
- `oc_teamhub_last_seen`
- `oc_teamhub_messages`
- `oc_teamhub_milestones`
- `oc_teamhub_msg_attach`
- `oc_teamhub_mywork_state`
- `oc_teamhub_pending_dels`
- `oc_teamhub_poll_votes`
- `oc_teamhub_presence_slots`
- `oc_teamhub_presence_team`
- `oc_teamhub_presence_template`
- `oc_teamhub_project`
- `oc_teamhub_project_member`
- `oc_teamhub_rooms`
- `oc_teamhub_team_apps`
- `oc_teamhub_team_expiry`
- `oc_teamhub_team_import_rows`
- `oc_teamhub_team_imports`
- `oc_teamhub_team_integrations`
- `oc_teamhub_team_type`
- `oc_teamhub_time_log`
- `oc_teamhub_web_links`
- `oc_teamhub_widget_layouts`
- `oc_termsofservice_sigs`
- `oc_termsofservice_terms`
- `oc_text2image_tasks`
- `oc_textprocessing_tasks`
- `oc_tickbuddy_ticks`
- `oc_tickbuddy_tracks`
- `oc_transfer_quota_limits`
- `oc_trusted_servers`
- `oc_twofactor_backupcodes`
- `oc_twofactor_tnn_tokens`
- `oc_twofactor_totp_secrets`
- `oc_user_transfer_owner`
- `oc_users_external`
- `oc_vcategory`
- `oc_vcategory_to_object`
- `oc_webauthn`
- `oc_webhook_listeners`
- `oc_webhook_tokens`
- `oc_cfg_shares`
- `oc_dashlink_links`
- `oc_df_duplicates`
- `oc_df_excluded_folders`
- `oc_df_folders`
- `oc_df_projects`
- `oc_documentserver_changes`
- `oc_documentserver_ipc`
- `oc_documentserver_locks`
- `oc_documentserver_sess`
- `oc_duplicatefinder`
- `oc_duplicatefinder_dups_f`
- `oc_duplicatefinder_filters`
- `oc_duplicatefinder_of`
- `oc_ex_event_handlers`
- `oc_ex_speech_to_text`
- `oc_ex_speech_to_text_q`
- `oc_ex_text_processing`
- `oc_ex_text_processing_q`
- `oc_ex_translation`
- `oc_ex_translation_q`
- `oc_folder_protection`
- `oc_listman_member`
- `oc_listman_message`
- `oc_listman_react`
- `oc_listman_sendjob`
- `oc_mediadc_photos`
- `oc_mediadc_settings`
- `oc_mediadc_tasks`
- `oc_mediadc_tasks_details`
- `oc_mediadc_videos`
- `oc_richdocuments_assets`
- `oc_richdocuments_direct`
- `oc_richdocuments_template`
- `oc_richdocuments_wopi`
- `oc_sms_relent_autorply`
- `oc_sms_relent_conv`
- `oc_sms_relent_received`
- `oc_sms_relent_restrict`
- `oc_sms_relent_sent`
- `oc_sms_relent_settings`
- `oc_sms_relent_subac`
- `oc_tsp_polls`
- `oc_tsp_votes`
- `oc_user_saml_group_members`
- `oc_user_saml_groups`
- `oc_user_saml_users`

## Errors (1 tables)

- `oc_tables_tables`: 
