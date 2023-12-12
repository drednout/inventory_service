local ulid_mod = require("ulid")
function time() 
    return os.time()*1000
end
ulid_mod.set_time_func(time)

wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

-- possible values for WRK_TEST_NAME: ["mix", "read", "write"]
wrk_test_name = os.getenv("WRK_TEST_NAME") or 'mix'

min_player_id = tonumber(os.getenv("WRK_TEST_MIN_PLAYER_ID")) or 1
max_player_id = tonumber(os.getenv("WRK_TEST_MAX_PLAYER_ID")) or 1000000
next_player_id = min_player_id

-- Function to generate a POST request with a JSON payload
function post_request(endpoint, payload)
   return wrk.format("POST", endpoint, nil, payload)
end


-- Function to generate a random item code
function random_item_code()
   local items = {"item123", "item456", "item789"}
   return items[math.random(1, 3)]
end

-- Function to generate random payload for /v1/inventory/get
function get_inventory_payload(player_id)
   return '{"player_id": ' .. player_id .. '}'
end

-- Function to generate random payload for /v1/inventory/grant
function grant_item_payload(player_id)
   return '{"player_id": ' .. player_id .. ', "item_code": "' .. random_item_code() .. '", "amount": ' .. math.random(1, 10) .. ', "ext_trx_id": "' .. tostring(ulid_mod.ulid()) .. '"}'
end

-- The main request function
function request()
  -- io.stderr:write(string.format("DEBUG: next_player_id is %s\n", next_player_id))  
  next_player_id = next_player_id + 1
  if next_player_id > max_player_id then
    next_player_id = min_player_id
    io.stderr:write(string.format("next_player_id is achive %d and reset to %d\n", max_player_id, min_player_id))  
  end
  local endpoint = choose_endpoint()
  local payload = generate_payload(endpoint, next_player_id)
  return post_request(endpoint, payload)
end

-- Function to randomly select an endpoint
function choose_endpoint()
  if wrk_test_name == "read" then
    return "/v1/inventory/get"
  elseif wrk_test_name == "write" then
    return "/v1/inventory/grant"
  elseif wrk_test_name == "write_stored_trx" then
    return "/internal/inventory/grant_stored_trx"
  elseif wrk_test_name == "mix" then
    local endpoints = {"/v1/inventory/get", "/v1/inventory/grant"}
    return endpoints[math.random(1, 2)]
  else
    error("Wrong wrk_test_name: " .. wrk_test_name)
  end
end

-- Function to generate a payload based on the selected endpoint
function generate_payload(endpoint, player_id)
   if endpoint == "/v1/inventory/get" then
      return get_inventory_payload(player_id)
   elseif endpoint == "/v1/inventory/grant" then
      return grant_item_payload(player_id)
   elseif endpoint == "/internal/inventory/grant_stored_trx" then
      return grant_item_payload(player_id)
   else
      return ""
   end
end
