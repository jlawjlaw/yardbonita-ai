<?php
/**
 * YardBonita GeneratePress Child Theme Functions
 * Only edit this file if you know what you're doing.
 */

if (!defined('ABSPATH')) exit;

// ===============================
// ✅ Custom Styles Enqueue
// ===============================

function yardbonita_enqueue_custom_styles() {
    if ( is_admin() ) return;

    $theme_uri = get_stylesheet_directory_uri();
    $theme_path = get_stylesheet_directory() . '/assets/css/';

    // Global styles
    wp_enqueue_style('yardbonita-header-footer', $theme_uri . '/assets/css/header-footer.css', [], filemtime($theme_path . 'header-footer.css'));
    wp_enqueue_style('yardbonita-newsletter', $theme_uri . '/assets/css/newsletter.css', [], filemtime($theme_path . 'newsletter.css'));
    wp_enqueue_style('yardbonita-search-widget', $theme_uri . '/assets/css/yardbonita-search-widget.css', [], filemtime($theme_path . 'yardbonita-search-widget.css'));
    wp_enqueue_style('yardbonita-sidebararticles', $theme_uri . '/assets/css/sidebararticles.css', [], filemtime($theme_path . 'sidebararticles.css'));

    // Homepage only
    if ( is_front_page() ) {
        wp_enqueue_style('yardbonita-citypage', $theme_uri . '/assets/css/citypage.css', [], filemtime($theme_path . 'citypage.css'));
        wp_enqueue_style('yardbonita-city-cards', $theme_uri . '/assets/css/city-cards.css', [], filemtime($theme_path . 'city-cards.css'));
    }

    // Single blog post
    if ( is_single() ) {
        wp_enqueue_style('yardbonita-postpageandsidebar', $theme_uri . '/assets/css/postpageandsidebar.css', [], filemtime($theme_path . 'postpageandsidebar.css'));
    }
}
add_action('wp_enqueue_scripts', 'yardbonita_enqueue_custom_styles', 11);

// ===============================
// ✅ Wrap Single Post in Styled Container
// ===============================
add_action('generate_before_main_content', function () {
    if (is_single()) {
        echo '<div class="post-outer-wrapper"><div class="post-inner"><div class="post-shell">';
    }
});

add_action('generate_after_main_content', function () {
    if (is_single()) {
        echo '</div></div></div><!-- close post-outer-wrapper -->';
    }
});