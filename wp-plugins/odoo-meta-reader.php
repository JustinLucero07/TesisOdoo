<?php
/**
 * Plugin Name: Odoo Meta Reader
 * Description: Expone un endpoint REST para leer todos los meta de un post (lectura solamente).
 * Version: 1.0
 * Author: InmoBi Dev
 */

add_action('rest_api_init', function () {
    register_rest_route('odoo-meta/v1', '/read/(?P<id>\d+)', array(
        'methods'  => 'GET',
        'callback' => 'odoo_read_post_meta',
        'permission_callback' => function ($request) {
            return current_user_can('edit_posts');
        },
        'args' => array(
            'id' => array(
                'validate_callback' => function ($param) {
                    return is_numeric($param);
                },
            ),
        ),
    ));
});

function odoo_read_post_meta($request) {
    $post_id = (int) $request['id'];
    $post = get_post($post_id);

    if (!$post) {
        return new WP_Error('not_found', 'Post not found', array('status' => 404));
    }

    $all_meta = get_post_meta($post_id);
    $result = array();

    foreach ($all_meta as $key => $values) {
        // Saltar campos internos de WordPress (prefijo _)
        // EXCEPTO _thumbnail_id que es útil
        if (strpos($key, '_') === 0 && $key !== '_thumbnail_id') {
            continue;
        }
        // Tomar el primer valor (get_post_meta devuelve arrays)
        $result[$key] = is_array($values) ? $values[0] : $values;
    }

    return rest_ensure_response($result);
}
