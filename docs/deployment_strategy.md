# QuestEd 環境分離デプロイ戦略

## 環境構成

### 推奨環境構成
```
Development → Staging → Production
    ↓           ↓          ↓
   開発環境    ステージング  本番環境
```

### 各環境の役割

#### 1. Development (開発環境)
- **目的**: 機能開発・デバッグ
- **場所**: ローカルマシン
- **データ**: テストデータ
- **設定**: `DevelopmentConfig`

#### 2. Staging (ステージング環境)
- **目的**: 本番環境と同一構成でのテスト
- **場所**: クラウド（本番と同等環境）
- **データ**: 本番データのサニタイズ版
- **設定**: `StagingConfig`

#### 3. Production (本番環境)
- **目的**: 実際のサービス提供
- **場所**: クラウド（高可用性構成）
- **データ**: 実データ
- **設定**: `ProductionConfig`

## デプロイ方法別比較

### Option 1: クラウドサービス利用（推奨）
- **AWS**: ECS + RDS + CloudFront
- **GCP**: Cloud Run + Cloud SQL + Cloud CDN  
- **Azure**: Container Instances + Azure Database + CDN

### Option 2: VPS/専用サーバー
- **利点**: コスト削減、フルコントロール
- **欠点**: 運用負荷、可用性確保が困難

### Option 3: PaaS利用
- **Heroku**: 簡単デプロイ
- **Railway**: モダンなPaaS
- **DigitalOcean App Platform**: バランス型

## 推奨デプロイ構成（AWS例）

### インフラ構成
```
Internet Gateway
       ↓
Application Load Balancer
       ↓
ECS Fargate (Multi-AZ)
  ↓        ↓
RDS MySQL  ElastiCache Redis
(Multi-AZ)   (Cluster)
```

### セキュリティグループ設定
```
ALB: 80,443 from 0.0.0.0/0
ECS: 8000 from ALB only
RDS: 3306 from ECS only  
Redis: 6379 from ECS only
```