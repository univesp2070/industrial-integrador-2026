# Guia de Contribuição

## Pré-requisitos

- Git
- Docker & Docker Compose
- Java 21 (para o Backend)
- Node.js 20+ (para o Frontend)
- PlatformIO (para o Firmware)

## Configuração do Ambiente

1. Clone o repositório:
```bash
git clone https://github.com/Zezoca29/edge-ai-industrial.git
cd edge-ai-industrial
```

2. Instale o Git Flow:
```bash
# Windows (via Git for Windows - já incluso)
# Linux
apt-get install git-flow
# macOS
brew install git-flow
```

3. Suba a infraestrutura local:
```bash
docker-compose up -d
```

## Fluxo de Trabalho (Git Flow)

### Criando uma Feature

```bash
# A partir da branch develop
git checkout develop
git pull origin develop
git checkout -b feature/nome-da-feature

# Desenvolva...
git add .
git commit -m "feat: descrição da mudança"

# Push e abra um PR para develop
git push origin feature/nome-da-feature
```

### Criando uma Release

```bash
git checkout develop
git checkout -b release/v1.0.0

# Ajustes finais, bump de versão...
git commit -m "chore: bump version to v1.0.0"

# Merge em main E develop
git checkout main
git merge release/v1.0.0
git tag -a v1.0.0 -m "Release v1.0.0"

git checkout develop
git merge release/v1.0.0

git push origin main develop --tags
```

### Hotfix

```bash
git checkout main
git checkout -b hotfix/descricao-do-fix

# Fix...
git commit -m "fix: descrição do fix"

# Merge em main E develop
git checkout main
git merge hotfix/descricao-do-fix
git tag -a v1.0.1 -m "Hotfix v1.0.1"

git checkout develop
git merge hotfix/descricao-do-fix
```

## Convenção de Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefixo | Uso |
|---------|-----|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug |
| `docs:` | Apenas documentação |
| `style:` | Formatação (sem mudança de lógica) |
| `refactor:` | Refatoração de código |
| `test:` | Adição/correção de testes |
| `ci:` | Mudanças em CI/CD |
| `chore:` | Tarefas diversas (dependências, configs) |

## Code Review

- Todo PR deve ser revisado por pelo menos 1 membro da equipe
- PRs devem ter descrição clara do que foi feito
- Testes devem passar antes do merge
- Squash merge é recomendado para features
