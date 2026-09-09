<?php
/**
 * Verify the OnlyOffice pipeline for several file types, not just the one xlsx.
 * For each file: build the editor config, have the Document Server download the
 * file with a signed request, and ask the Document Server to convert it (which
 * only succeeds if it could actually parse the document).
 */

require_once '/www/wwwroot/cloud.amarisstock.com/lib/base.php';

use OCA\Onlyoffice\Vendor\Firebase\JWT\JWT;

$uid = 'admin';

// fileId => target conversion format
$targets = [
    170 => 'csv',   // Amaris Chemicals Posting Schedule (2).xlsx
    4 => 'pdf',     // Welcome to Nextcloud Hub.docx
    7 => null,      // Nextcloud flyer.pdf (view only, skip conversion)
];

$appManager = \OC::$server->get(\OCP\App\IAppManager::class);
$appManager->loadApp('onlyoffice');
$appManager->loadApp('files');
\OC::$server->get(\OCP\Route\IRouter::class)->loadRoutes('onlyoffice');

\OC_Util::tearDownFS();
\OC_User::setUserId($uid);
\OC_Util::setupFS($uid);
$userSession = \OC::$server->get(\OCP\IUserSession::class);
$userManager = \OC::$server->get(\OCP\IUserManager::class);
$userSession->setUser($userManager->get($uid));

$appConfig = \OC::$server->get(\OCA\Onlyoffice\AppConfig::class);
$docService = \OC::$server->get(\OCA\Onlyoffice\DocumentService::class);
$controller = \OC::$server->get(\OCA\Onlyoffice\Controller\EditorApiController::class);
$client = \OC::$server->get(\OCP\Http\Client\IClientService::class)->newClient();

$secret = $appConfig->getDocumentServerSecret();
$jwtHeaderName = $appConfig->jwtHeader();
$failures = 0;

foreach ($targets as $fileId => $convertTo) {
    echo str_repeat('-', 72) . "\n";
    $data = $controller->config($fileId)->getData();
    if (isset($data['error'])) {
        printf("fileId %d: CONFIG ERROR %s\n", $fileId, $data['error']);
        $failures++;
        continue;
    }

    $title = $data['document']['title'];
    $fileType = $data['document']['fileType'];
    printf("%s\n", $title);
    printf("  type %s / documentType %s / edit %s\n",
        $fileType, $data['documentType'],
        var_export($data['document']['permissions']['edit'] ?? null, true));

    $docUrl = $data['document']['url'];
    $now = time();
    $token = JWT::encode(
        ['payload' => ['url' => $docUrl], 'iat' => $now, 'exp' => $now + 300],
        $secret,
        'HS256'
    );

    try {
        $resp = $client->get($docUrl, [
            'headers' => [$jwtHeaderName => 'Bearer ' . $token],
            'nextcloud' => ['allow_local_address' => true],
            'timeout' => 60,
        ]);
        printf("  download : HTTP %d, %d bytes\n", $resp->getStatusCode(), strlen((string)$resp->getBody()));
    } catch (\Throwable $e) {
        printf("  download : FAIL %s\n", $e->getMessage());
        $failures++;
        continue;
    }

    if ($convertTo === null) {
        echo "  convert  : skipped (view-only format)\n";
        continue;
    }

    try {
        $uri = $docService->getConvertedUri($docUrl, $fileType, $convertTo, 'fmt_' . random_int(1, 999999));
        $resp = $client->get((string)$uri, ['nextcloud' => ['allow_local_address' => true], 'timeout' => 60]);
        printf("  convert  : %s -> %s OK, HTTP %d, %d bytes\n",
            $fileType, $convertTo, $resp->getStatusCode(), strlen((string)$resp->getBody()));
    } catch (\Throwable $e) {
        printf("  convert  : FAIL %s\n", $e->getMessage());
        $failures++;
    }
}

echo str_repeat('-', 72) . "\n";
echo $failures === 0 ? "ALL FORMAT CHECKS PASSED\n" : "FAILURES: $failures\n";
exit($failures === 0 ? 0 : 1);
