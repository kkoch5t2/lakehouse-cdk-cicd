select 1 as forced_failure where '{{ env_var('FORCE_FAIL', '0') }}' = '1'
