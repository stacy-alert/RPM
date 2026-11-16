<?php
declare(strict_types=1);

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception as PHPMailerException;

header('Content-Type: application/json');
header('X-Robots-Tag: noindex, nofollow');

require __DIR__ . '/config.php';

function respond(bool $ok, string $error = ''): void {
    echo json_encode(['ok' => $ok, 'error' => $error]);
    exit;
}

// MAIL_CONFIGURED is false when BLUEHOST_SMTP_USERNAME/PASSWORD/NOTIFY_EMAIL_TO
// aren't set as GitHub secrets -- the dog list still works without them, but
// this endpoint has nothing to send through, so fail cleanly instead of
// hitting an undefined-constant fatal error further down.
if (!defined('MAIL_CONFIGURED') || !MAIL_CONFIGURED) {
    http_response_code(503);
    respond(false, 'Inquiries are not available right now.');
}

require __DIR__ . '/vendor/phpmailer/Exception.php';
require __DIR__ . '/vendor/phpmailer/PHPMailer.php';
require __DIR__ . '/vendor/phpmailer/SMTP.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    respond(false, 'Method not allowed.');
}

function field(string $name): string {
    return trim((string)($_POST[$name] ?? ''));
}

$referenceCode = field('reference_code');
$visitorName = field('name');
$visitorEmail = field('email');
$org = field('org');
$experience = field('experience');
$message = field('message');

if ($referenceCode === '' || $visitorName === '' || $visitorEmail === '' || $message === '') {
    respond(false, 'Please fill in all required fields.');
}

if (!filter_var($visitorEmail, FILTER_VALIDATE_EMAIL)) {
    respond(false, 'That email address doesn\'t look right.');
}

if (!preg_match('/^[A-Z]{1,3}-\d{4}$/', $referenceCode)) {
    respond(false, 'Unrecognized reference code.');
}

// Strip anything that could be used for header injection in the few
// fields that might end up anywhere near an email header.
function singleLine(string $s): string {
    return preg_replace('/[\r\n]+/', ' ', $s);
}
$visitorName = singleLine($visitorName);
$visitorEmail = singleLine($visitorEmail);
$org = singleLine($org);

$lookupPath = PRIVATE_DATA_PATH . '/lookup.json';
$dogName = '(unknown — reference code not found in current lookup data)';
$dogCacId = '';
$dogSeqId = '';
$dogUrl = '';

if (is_readable($lookupPath)) {
    $lookup = json_decode((string)file_get_contents($lookupPath), true);
    if (is_array($lookup) && isset($lookup[$referenceCode])) {
        $entry = $lookup[$referenceCode];
        $dogName = (string)($entry['name'] ?? $dogName);
        $dogCacId = (string)($entry['cac_id'] ?? '');
        $dogSeqId = (string)($entry['shelter_seq_id'] ?? '');
        $dogUrl = (string)($entry['listing_url'] ?? '');
    }
}

$body = "Reference code: {$referenceCode}\n" .
    "Dog name: {$dogName}\n" .
    "CAC animal ID (shelter's own number): {$dogSeqId}\n" .
    "CAC internal ID (AnimalsFirst): {$dogCacId}\n" .
    "CAC listing URL: {$dogUrl}\n\n" .
    "--- Inquirer ---\n" .
    "Name: {$visitorName}\n" .
    "Email: {$visitorEmail}\n" .
    "Rescue/organization: " . ($org ?: '(none given)') . "\n" .
    "Experience with this breed: " . ($experience ?: '(none given)') . "\n\n" .
    "Message:\n{$message}\n";

$mail = new PHPMailer(true);
try {
    $mail->isSMTP();
    $mail->Host = SMTP_HOST;
    $mail->Port = SMTP_PORT;
    $mail->SMTPAuth = true;
    $mail->Username = SMTP_USERNAME;
    $mail->Password = SMTP_PASSWORD;
    // Port 465 (Bluehost's documented SMTP port) is implicit TLS, not
    // STARTTLS — using STARTTLS here is the port-465-won't-connect bug.
    // 587 is the STARTTLS port if SMTP_PORT is ever overridden to it.
    $mail->SMTPSecure = (SMTP_PORT === 465)
        ? PHPMailer::ENCRYPTION_SMTPS
        : PHPMailer::ENCRYPTION_STARTTLS;

    $mail->setFrom(SMTP_USERNAME, 'Shelter Breed Preview');
    $mail->addAddress(NOTIFY_EMAIL_TO);
    $mail->addReplyTo($visitorEmail, $visitorName);

    $mail->Subject = "Ask about dog {$referenceCode}";
    $mail->Body = $body;

    $mail->send();
    respond(true);
} catch (PHPMailerException $e) {
    error_log('ask-about-dog mail failure: ' . $mail->ErrorInfo);
    respond(false, 'Could not send right now. Try again shortly.');
}
