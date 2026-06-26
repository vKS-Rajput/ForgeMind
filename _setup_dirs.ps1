$dirs = @(
    "src\forgemind\graph\domain",
    "src\forgemind\graph\ports",
    "src\forgemind\graph\adapters",
    "src\forgemind\retrieval\domain",
    "src\forgemind\retrieval\ports",
    "src\forgemind\retrieval\adapters",
    "src\forgemind\reasoning\domain",
    "src\forgemind\reasoning\ports",
    "src\forgemind\reasoning\adapters",
    "src\forgemind\api\routes",
    "src\forgemind\api\schemas",
    "tests\unit\knowledge",
    "tests\unit\graph",
    "tests\unit\retrieval",
    "tests\unit\reasoning",
    "tests\integration",
    "tests\architecture",
    "tests\golden\queries",
    "tests\golden\expected",
    "docs\architecture",
    "docs\adr",
    "docs\standards",
    "docs\onboarding",
    "docs\api",
    "data\demo\manuals",
    "data\demo\incidents",
    "data\demo\work_orders",
    "data\demo\golden_queries",
    "scripts",
    "examples",
    ".github\workflows"
)
foreach ($d in $dirs) {
    New-Item -Path $d -ItemType Directory -Force | Out-Null
}
Write-Host "All directories created."
