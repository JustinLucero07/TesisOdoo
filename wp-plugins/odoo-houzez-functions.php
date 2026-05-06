<?php
// code will goes here
// 
// ======================================================
// 1) Habilitar REST API para property (debe ir en init)
// ======================================================
add_filter('register_post_type_args', function($args, $post_type) {
    if ($post_type === 'property') {
        $args['show_in_rest'] = true;
        $args['rest_base'] = 'property';
    }
    return $args;
}, 10, 2);

// ======================================================
// 2) Endpoints custom para meta fields de Odoo
//    - POST: Guardar meta (ya existía)
//    - GET:  Leer TODOS los meta (NUEVO para importación)
// ======================================================
add_action('rest_api_init', function() {
    // POST - Guardar meta desde Odoo
    register_rest_route('odoo-houzez/v1', '/meta/(?P<id>\d+)', array(
        'methods' => 'POST',
        'callback' => 'odoo_houzez_save_meta',
        'permission_callback' => function($request) {
            return current_user_can('edit_posts');
        },
    ));

    // GET - Leer todos los meta para importación a Odoo
    register_rest_route('odoo-houzez/v1', '/meta/(?P<id>\d+)', array(
        'methods' => 'GET',
        'callback' => 'odoo_houzez_read_meta',
        'permission_callback' => function($request) {
            return current_user_can('edit_posts');
        },
    ));
});

// --- GUARDAR META (POST) ---
function odoo_houzez_save_meta($request) {
    $post_id = (int) $request['id'];
    if (!get_post($post_id)) {
        return new WP_Error('not_found', 'Post no encontrado', array('status' => 404));
    }
    $body = $request->get_json_params();
    $updated = 0;
    foreach ($body as $key => $value) {
        if ($key === 'fave_property_images' && is_array($value)) {
            delete_post_meta($post_id, 'fave_property_images');
            foreach ($value as $media_id) {
                add_post_meta($post_id, 'fave_property_images', $media_id);
            }
            $updated++;
        } else {
            update_post_meta($post_id, $key, $value);
            $updated++;
        }
    }
    return array('success' => true, 'post_id' => $post_id, 'updated' => $updated);
}

// --- LEER META (GET) - NUEVO ---
function odoo_houzez_read_meta($request) {
    $post_id = (int) $request['id'];
    $post = get_post($post_id);

    if (!$post) {
        return new WP_Error('not_found', 'Post no encontrado', array('status' => 404));
    }

    $all_meta = get_post_meta($post_id);
    $result = array();

    foreach ($all_meta as $key => $values) {
        // Saltar campos internos de WordPress (prefijo _) excepto _thumbnail_id
        if (strpos($key, '_') === 0 && $key !== '_thumbnail_id') {
            continue;
        }
        // get_post_meta devuelve arrays, tomar el primer valor
        $result[$key] = is_array($values) ? $values[0] : $values;
    }

    return rest_ensure_response($result);
}


// ======================================================
// 3) Endpoint custom para taxonomías (sin cambios)
// ======================================================

// ======================================================
// INTEGRACIÓN HOUZEZ → ODOO CRM
// ======================================================

// CONFIGURA AQUÍ TUS VALORES:
define('ODOO_WEBHOOK_URL',    'https://renovator-trimmer-procurer.ngrok-free.dev');
define('ODOO_WEBHOOK_SECRET', 'inmobi_secret_2024');

// Hook en formulario de contacto Houzez
add_action('wp_ajax_houzez_ajax_contact_agent',        'odoo_crm_capture_houzez_inquiry', 5);
add_action('wp_ajax_nopriv_houzez_ajax_contact_agent', 'odoo_crm_capture_houzez_inquiry', 5);
add_action('wp_ajax_houzez_contact_agent',             'odoo_crm_capture_houzez_inquiry', 5);
add_action('wp_ajax_nopriv_houzez_contact_agent',      'odoo_crm_capture_houzez_inquiry', 5);

function odoo_crm_capture_houzez_inquiry() {
    if (!defined('ODOO_WEBHOOK_URL') || empty(ODOO_WEBHOOK_URL)) return;

    $listing_id    = intval($_POST['listing_id']   ?? $_POST['property_id'] ?? 0);
    $sender_name   = sanitize_text_field($_POST['sender_name']  ?? $_POST['name']  ?? '');
    $sender_email  = sanitize_email($_POST['sender_email']      ?? $_POST['email'] ?? '');
    $sender_phone  = sanitize_text_field($_POST['sender_phone'] ?? $_POST['phone'] ?? '');
    $message       = sanitize_textarea_field($_POST['message']  ?? '');
    $action_type   = sanitize_text_field($_POST['action_type']  ?? '');
    $property_title = $listing_id ? get_the_title($listing_id) : '';

    wp_remote_post(ODOO_WEBHOOK_URL, [
        'headers'  => ['Content-Type' => 'application/json'],
        'body'     => wp_json_encode([
            'secret'         => ODOO_WEBHOOK_SECRET,
            'name'           => $sender_name,
            'email'          => $sender_email,
            'phone'          => $sender_phone,
            'message'        => $message,
            'wp_post_id'     => $listing_id,
            'property_title' => $property_title,
            'role'           => $action_type,
        ]),
        'timeout'  => 8,
        'blocking' => false,
    ]);
}

?>
