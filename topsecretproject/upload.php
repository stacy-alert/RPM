<?php
declare(strict_types=1);
// Receives the dog list sent by the owner's "Send dogs" bookmark (run in
// their own browser on the shelter's listing page) and saves it to the
// private folder as cac_raw.json for the daily workflow to classify.
// Requires the token stored in <private folder>/upload_token.txt.

header('X-Robots-Tag: noindex, nofollow');
header('Content-Type: text/html; charset=utf-8');

function page(string $msg, int $code = 200): void {
    http_response_code($code);
    echo '<!doctype html><meta name="robots" content="noindex,nofollow">'
       . '<meta name="viewport" content="width=device-width,initial-scale=1">'
       . '<title>Dog list upload</title><body style="font:18px system-ui;margin:2rem">'
       . htmlspecialchars($msg) . '</body>';
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') page('Nothing here.', 405);

// Data folder: <site root>/topsecret_private, the folder the daily
// workflow's FTP login reads. Web access to it is denied by .htaccess,
// which is (re)written here before anything is saved.
$private = dirname(__DIR__) . '/topsecret_private';
if (!is_dir($private) && !mkdir($private, 0750)) page('Server not set up (could not create data folder).', 500);
$deny = "Require all denied\n<IfModule !mod_authz_core.c>\nDeny from all\n</IfModule>\n";
if (@file_get_contents($private . '/.htaccess') !== $deny && file_put_contents($private . '/.htaccess', $deny) === false) {
    page('Server not set up (could not protect data folder).', 500);
}

// Token: created by pi/make_bookmark.py. Look in the data folder and in
// any topsecret_private folder above this one (home-level FTP account).
$expected = '';
$dir = __DIR__;
$candidates = [$private];
for ($i = 0; $i < 6; $i++) {
    $dir = dirname($dir);
    $candidates[] = $dir . '/topsecret_private';
    $candidates[] = $dir . $dir . '/topsecret_private';
}
foreach ($candidates as $c) {
    $f = $c . '/upload_token.txt';
    if (@is_readable($f)) { $expected = trim((string)file_get_contents($f)); if (strlen($expected) >= 20) break; }
}
if (strlen($expected) < 20) page('Server not set up (no upload token found). Run make_bookmark.py again.', 500);
$given = (string)($_POST['token'] ?? '');
if (!hash_equals($expected, $given)) page('Not authorized.', 403);

$data = json_decode((string)($_POST['data'] ?? ''), true);
if (!is_array($data) || !isset($data['dogs']) || !is_array($data['dogs'])) page('That did not look like a dog list.', 400);
if (count($data['dogs']) === 0) page('The list was empty, so nothing was saved. Scroll to the bottom of the shelter page first, then tap the bookmark again.', 400);
if (count($data['dogs']) > 5000) page('List too large.', 400);

function s($v, int $max = 200): ?string {
    if (!is_string($v) || $v === '') return null;
    return mb_substr($v, 0, $max);
}

$dogs = [];
foreach ($data['dogs'] as $d) {
    if (!is_array($d)) continue;
    $id = s($d['cac_id'] ?? null, 64);
    if ($id === null || !preg_match('/^[A-Za-z0-9_-]+$/', $id)) continue;
    $photos = [];
    foreach ((array)($d['photo_urls'] ?? []) as $u) {
        if (!is_string($u) || strlen($u) < 12 || strlen($u) >= 600) continue;
        $p = @parse_url($u);
        if (!$p || ($p['scheme'] ?? '') !== 'https' || empty($p['host'])) continue;
        $host = strtolower($p['host']);
        $okHost = false;
        foreach (['amazonaws.com', 'cincinnatianimalcare.org', 'cloudfront.net', 'googleusercontent.com', 'wp.com'] as $h) {
            if ($host === $h || substr($host, -strlen('.' . $h)) === '.' . $h) { $okHost = true; break; }
        }
        $isImg = (bool)preg_match('/\.(jpe?g|png|webp|gif)(\?|$)/i', $u);
        if ($okHost || $isImg) $photos[] = $u;
    }
    $url = s($d['listing_url'] ?? null, 500);
    if ($url !== null && strpos($url, 'https://cincinnatianimalcare.org/') !== 0) $url = null;
    $dogs[] = [
        'cac_id' => $id,
        'shelter_seq_id' => s($d['shelter_seq_id'] ?? null, 32),
        'name' => s($d['name'] ?? null, 100),
        'listing_url' => $url,
        'photo_urls' => array_slice($photos, 0, 5),
        'sex' => s($d['sex'] ?? null, 20),
        'age' => s($d['age'] ?? null, 20),
        'size' => s($d['size'] ?? null, 20),
        'date_listed' => s($d['date_listed'] ?? null, 40),
    ];
}
if (count($dogs) === 0) page('No valid dogs in that list; nothing saved.', 400);

$claimed = isset($data['claimed_total']) && is_int($data['claimed_total']) ? $data['claimed_total'] : null;
$out = json_encode(['fetched_at' => gmdate('c'), 'claimed_total' => $claimed, 'dogs' => $dogs]);
if (file_put_contents($private . '/cac_raw.json', $out, LOCK_EX) === false) page('Could not save the list.', 500);

$msg = 'Saved ' . count($dogs) . ' dogs.';
if ($claimed !== null && count($dogs) < $claimed) $msg .= ' The shelter page says it has ' . $claimed . ', so scroll all the way to the bottom and tap the bookmark again to get the rest.';
$msg .= ' The site updates the next time the breed check runs.';
page($msg);
