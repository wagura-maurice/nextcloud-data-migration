<?php
/**
 * End-to-end verification of the OnlyOffice open-document flow, replicating
 * exactly what the Document Server does (including the signed Authorization
 * header that CallbackController::download requires when JWT is enabled).
 */

require_once '/www/wwwroot/cloud.amarisstock.com/lib/base.php';

use OCA\Onlyoffice\Vendor\Firebase\JWT\JWT;

$uid = 'admin';
$fileId = 170;

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
$client = \OC::$server->get(\OCP\Http\Client\IClientService::class)->newClient();

$controller = \OC::$server->get(\OCA\Onlyoffice\Controller\EditorApiController::class);
$data = $controller->config($fileId)->getData();
if (isset($data['error'])) {
    echo 'CONFIG ERROR: ' . $data['error'] . "\n";
    exit(1);
}

$docUrl = $data['document']['url'];
$secret = $appConfig->getDocumentServerSecret();
$jwtHeaderName = $appConfig->jwtHeader();

echo "=== Config summary ===\n";
printf("  file        : %s\n", $data['document']['title']);
printf("  fileType    : %s / documentType %s\n", $data['document']['fileType'], $data['documentType']);
printf("  key         : %s\n", $data['document']['key']);
printf("  edit perm   : %s\n", var_export($data['document']['permissions']['edit'], true));
printf("  JWT enabled : %s (header %s)\n", $secret === '' ? 'no' : 'yes', $jwtHeaderName);

echo "\n=== Step 1: Document Server downloads the file (signed request) ===\n";
$now = time();
$token = JWT::encode(['payload' => ['url' => $docUrl], 'iat' => $now, 'exp' => $now + 300], $secret, 'HS256');
try {
    $resp = $client->get($docUrl, [
        'headers' => [$jwtHeaderName => 'Bearer ' . $token],
        'nextcloud' => ['allow_local_address' => true],
        'timeout' => 60,
    ]);
    $body = (string)$resp->getBody();
    $magic = bin2hex(substr($body, 0, 4));
    printf("  HTTP %d, bytes %d, magic %s %s\n", $resp->getStatusCode(), strlen($body), $magic,
        $magic === '504b0304' ? '(valid XLSX)' : '(NOT XLSX!)');
    if ($magic !== '504b0304') {
        echo '  body head: ' . substr($body, 0, 200) . "\n";
        exit(1);
    }
} catch (\Throwable $e) {
    echo '  FAIL: ' . $e->getMessage() . "\n";
    exit(1);
}

echo "\n=== Step 2: Browser loads the editor API script ===\n";
$apiJs = $data['documentServerUrl'] . 'web-apps/apps/api/documents/api.js';
try {
    $resp = $client->get($apiJs, ['nextcloud' => ['allow_local_address' => true], 'timeout' => 30]);
    $body = (string)$resp->getBody();
    printf("  %s\n", $apiJs);
    printf("  HTTP %d, bytes %d, DocsAPI: %s\n", $resp->getStatusCode(), strlen($body),
        str_contains($body, 'DocsAPI') ? 'YES' : 'NO');
} catch (\Throwable $e) {
    echo '  FAIL: ' . $e->getMessage() . "\n";
    exit(1);
}

echo "\n=== Step 3: Document Server opens/parses the file (real conversion) ===\n";
$docService = \OC::$server->get(\OCA\Onlyoffice\DocumentService::class);
try {
    $converted = $docService->getConvertedUri($docUrl, 'xlsx', 'csv', 'verify_' . random_int(1, 999999));
    printf("  DS returned conversion URI (proves it read the xlsx)\n");
    $resp = $client->get((string)$converted, ['nextcloud' => ['allow_local_address' => true], 'timeout' => 60]);
    $csv = (string)$resp->getBody();
    printf("  HTTP %d, csv bytes %d\n", $resp->getStatusCode(), strlen($csv));
    echo "  --- first 3 lines of converted content ---\n";
    foreach (array_slice(preg_split('/\r\n|\n|\r/', $csv), 0, 3) as $line) {
        echo '    ' . substr($line, 0, 100) . "\n";
    }
} catch (\Throwable $e) {
    echo '  FAIL conversion: ' . get_class($e) . ': ' . $e->getMessage() . "\n";
    exit(1);
}

echo "\n=== Step 4: Command service version handshake ===\n";
try {
    $cmd = $docService->commandRequest('version');
    printf("  DS version: %s (error code %s)\n", $cmd['version'] ?? '?', $cmd['error'] ?? '?');
} catch (\Throwable $e) {
    echo '  FAIL: ' . $e->getMessage() . "\n";
    exit(1);
}

echo "\n=== Step 5: Full settings self-check ===\n";
[$err, $ver] = $docService->checkDocServiceUrl();
printf("  checkDocServiceUrl: %s (version %s)\n", $err === '' ? 'PASS' : "FAIL -> $err", $ver);
if ($err !== '') {
    exit(1);
}

echo "\nRESULT: '" . $data['document']['title'] . "' opens in OnlyOffice successfully.\n";
