<template>
  <div class="global-market" :class="{ 'theme-dark': isDarkTheme }">
    <!-- Header with refresh button -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <a-icon type="global" />
          {{ $t('globalMarket.title') }}
        </h1>
        <span
          v-if="lastUpdateTime"
          class="update-time"
        >
          {{ $t('globalMarket.lastUpdate') }}: {{ formatTime(lastUpdateTime) }}
        </span>
      </div>
      <div class="header-actions">
        <a-button
          type="primary"
          :loading="refreshing"
          @click="handleRefresh"
        >
          <a-icon
            type="sync"
            :spin="refreshing"
          />
          {{ $t('globalMarket.refresh') }}
        </a-button>
      </div>
    </div>

    <!-- Map + Heatmap Row -->
    <div class="map-heatmap-row">
      <!-- World Map Section -->
      <div class="map-section">
        <div class="section-header">
          <h2><a-icon type="global" /> {{ $t('globalMarket.indices') }}</h2>
          <a-spin v-if="loadingStates.overview" size="small" class="section-spinner" />
        </div>
        <div class="map-wrapper">
          <div
            ref="worldMap"
            class="world-map-container"
            :class="{ 'map-loading': loadingStates.overview }"
          ></div>
          <div
            v-if="loadingStates.overview"
            class="skeleton-map-overlay"
          >
            <div class="skeleton-shimmer"></div>
          </div>
        </div>
      </div>

      <!-- Heatmap Section -->
      <div class="heatmap-section">
        <div class="section-header">
          <h2><a-icon type="appstore" /> {{ $t('globalMarket.heatmap') }}</h2>
          <a-spin v-if="loadingStates.heatmap" size="small" class="section-spinner" />
        </div>
        <div v-if="loadingStates.heatmap" class="skeleton-heatmap">
          <div v-for="i in 12" :key="'skel-heat-'+i" class="skeleton-heatmap-item">
            <div class="skeleton-shimmer"></div>
          </div>
        </div>
        <a-tabs
          v-else
          v-model="activeHeatmapTab"
          :animated="false"
          class="heatmap-tabs"
        >
          <!-- Crypto Heatmap -->
          <a-tab-pane
            key="crypto"
            :tab="$t('globalMarket.cryptoHeatmap')"
          >
            <div class="heatmap-container">
              <div
                v-for="coin in heatmap.crypto"
                :key="coin.name"
                class="heatmap-item"
                :style="{ ...getHeatmapStyle(coin.value), flexBasis: getHeatmapSize(coin.marketCap, 'crypto') }"
              >
                <div class="heatmap-symbol">{{ coin.name }}</div>
                <div class="heatmap-value">{{ coin.value >= 0 ? '+' : '' }}{{ formatNumber(coin.value, 2) }}%</div>
                <div class="heatmap-price">${{ formatCompact(coin.price) }}</div>
              </div>
            </div>
          </a-tab-pane>

          <!-- Sector Heatmap -->
          <a-tab-pane
            key="sectors"
            :tab="$t('globalMarket.sectorHeatmap')"
          >
            <div class="heatmap-container sectors-heatmap">
              <div
                v-for="sector in heatmap.sectors"
                :key="sector.name"
                class="heatmap-item sector-item"
                :style="getHeatmapStyle(sector.value)"
              >
                <div class="heatmap-symbol">{{ isZhLocale ? sector.name : sector.name_en }}</div>
                <div class="heatmap-value">{{ sector.value >= 0 ? '+' : '' }}{{ formatNumber(sector.value, 2) }}%</div>
                <div class="sector-stocks">{{ (sector.stocks || []).slice(0, 3).join(', ') }}</div>
              </div>
            </div>
          </a-tab-pane>

          <!-- Forex Heatmap -->
          <a-tab-pane
            key="forex"
            :tab="$t('globalMarket.forexHeatmap')"
          >
            <div class="heatmap-container forex-heatmap">
              <div
                v-for="(pair, index) in heatmap.forex"
                :key="'forex-' + index"
                class="heatmap-item"
                :style="getHeatmapStyle(pair.value)"
              >
                <div class="heatmap-symbol">{{ isZhLocale ? pair.name_cn : pair.name_en }}</div>
                <div class="heatmap-value">{{ pair.value >= 0 ? '+' : '' }}{{ formatNumber(pair.value, 2) }}%</div>
                <div class="heatmap-price">{{ formatNumber(pair.price, 4) }}</div>
              </div>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </div>

    <!-- Market Sentiment Row -->
    <div class="sentiment-row">
      <!-- Fear & Greed Index -->
      <div class="sentiment-card fear-greed">
        <div class="sentiment-header">
          <span class="sentiment-title">{{ $t('globalMarket.fearGreedIndex') }}</span>
          <a-spin v-if="loadingStates.sentiment" size="small" class="section-spinner" />
          <a-tooltip v-else :title="$t('globalMarket.fearGreedTip')">
            <a-icon type="info-circle" />
          </a-tooltip>
        </div>
        <!-- 情绪骨架屏 -->
        <div v-if="loadingStates.sentiment" class="skeleton-sentiment">
          <div class="skeleton-gauge"></div>
          <div class="skeleton-line" style="width: 60%; margin: 10px auto;"></div>
        </div>
        <div v-else class="gauge-container">
          <div class="gauge-meter">
            <svg
              viewBox="0 0 200 110"
              class="gauge-svg"
            >
              <!-- Background arc -->
              <defs>
                <linearGradient
                  id="gaugeGradient"
                  x1="0%"
                  y1="0%"
                  x2="100%"
                  y2="0%"
                >
                  <stop
                    offset="0%"
                    style="stop-color:#dc2626"
                  />
                  <stop
                    offset="25%"
                    style="stop-color:#f87171"
                  />
                  <stop
                    offset="50%"
                    style="stop-color:#fbbf24"
                  />
                  <stop
                    offset="75%"
                    style="stop-color:#84cc16"
                  />
                  <stop
                    offset="100%"
                    style="stop-color:#22c55e"
                  />
                </linearGradient>
              </defs>
              <!-- Gauge arc -->
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="url(#gaugeGradient)"
                stroke-width="16"
                stroke-linecap="round"
              />
              <!-- Needle -->
              <g :transform="`rotate(${getNeedleRotation(sentiment.fear_greed?.value || 50)}, 100, 100)`">
                <line
                  x1="100"
                  y1="100"
                  x2="100"
                  y2="30"
                  :stroke="isDarkTheme ? '#f1f5f9' : '#1e293b'"
                  stroke-width="3"
                  stroke-linecap="round"
                />
                <circle
                  cx="100"
                  cy="100"
                  r="8"
                  :fill="isDarkTheme ? '#f1f5f9' : '#1e293b'"
                />
              </g>
            </svg>
            <div class="gauge-center">
              <span
                class="gauge-value"
                :class="getFearGreedClass(sentiment.fear_greed?.value)"
              >{{ sentiment.fear_greed?.value || '--' }}</span>
              <span class="gauge-label">{{ getFearGreedLabel(sentiment.fear_greed?.value) }}</span>
            </div>
          </div>
          <div class="gauge-legend">
            <span class="legend-item extreme-fear">{{ $t('globalMarket.extremeFear') }}</span>
            <span class="legend-item fear">{{ $t('globalMarket.fear') }}</span>
            <span class="legend-item neutral">{{ $t('globalMarket.neutral') }}</span>
            <span class="legend-item greed">{{ $t('globalMarket.greed') }}</span>
            <span class="legend-item extreme-greed">{{ $t('globalMarket.extremeGreed') }}</span>
          </div>
        </div>
      </div>

      <!-- VIX -->
      <div class="sentiment-card vix">
        <div class="sentiment-header">
          <span class="sentiment-title">{{ $t('globalMarket.vixTitle') || 'VIX 波动率指数' }}</span>
          <a-spin v-if="loadingStates.sentiment" size="small" class="section-spinner" />
          <a-tooltip v-else :title="$t('globalMarket.vixTip') || '衡量标普500期权的隐含波动率'">
            <a-icon type="info-circle" />
          </a-tooltip>
        </div>
        <!-- VIX 骨架屏 -->
        <div v-if="loadingStates.sentiment" class="skeleton-sentiment">
          <div class="skeleton-line" style="width: 40%; height: 48px; margin: 20px auto;"></div>
          <div class="skeleton-line" style="width: 30%; margin: 8px auto;"></div>
        </div>
        <div v-else class="vix-display">
          <div
            class="vix-value"
            :class="sentiment.vix?.level"
          >
            {{ sentiment.vix?.value || '--' }}
          </div>
          <div
            class="vix-change"
            :class="(sentiment.vix?.change || 0) >= 0 ? 'positive' : 'negative'"
          >
            {{ (sentiment.vix?.change || 0) >= 0 ? '+' : '' }}{{ formatNumber(sentiment.vix?.change, 2) }}%
          </div>
          <div class="vix-interpretation">{{ isZhLocale ? sentiment.vix?.interpretation : sentiment.vix?.interpretation_en }}</div>
        </div>
      </div>
    </div>

    <!-- Additional Indicators Row -->
    <div class="indicators-row">
      <!-- 美元指数 DXY -->
      <div class="indicator-card">
        <div class="indicator-header">
          <span class="indicator-icon">💵</span>
          <span class="indicator-title">{{ isZhLocale ? '美元指数 DXY' : 'US Dollar Index' }}</span>
        </div>
        <template v-if="loadingStates.sentiment">
          <div class="skeleton-indicator">
            <div class="skeleton-line" style="width: 50%; height: 32px;"></div>
          </div>
        </template>
        <template v-else>
          <div class="indicator-value" :class="getDxyClass(sentiment.dxy?.level)">
            {{ sentiment.dxy?.value || '--' }}
          </div>
          <div class="indicator-change" :class="(sentiment.dxy?.change || 0) >= 0 ? 'positive' : 'negative'">
            {{ (sentiment.dxy?.change || 0) >= 0 ? '+' : '' }}{{ formatNumber(sentiment.dxy?.change, 2) }}%
          </div>
          <div class="indicator-desc">{{ isZhLocale ? sentiment.dxy?.interpretation : sentiment.dxy?.interpretation_en }}</div>
        </template>
      </div>

      <!-- 收益率曲线 -->
      <div class="indicator-card yield-curve">
        <div class="indicator-header">
          <span class="indicator-icon">📈</span>
          <span class="indicator-title">{{ isZhLocale ? '美债收益率曲线' : 'Treasury Yield Curve' }}</span>
        </div>
        <template v-if="loadingStates.sentiment">
          <div class="skeleton-indicator">
            <div class="skeleton-line" style="width: 60%; height: 32px;"></div>
          </div>
        </template>
        <template v-else>
          <div class="yield-values">
            <div class="yield-item">
              <span class="yield-label">10Y</span>
              <span class="yield-num">{{ sentiment.yield_curve?.yield_10y || '--' }}%</span>
            </div>
            <div class="yield-spread" :class="getYieldCurveClass(sentiment.yield_curve?.level)">
              <span class="spread-label">{{ isZhLocale ? '利差' : 'Spread' }}</span>
              <span class="spread-value">{{ sentiment.yield_curve?.spread >= 0 ? '+' : '' }}{{ formatNumber(sentiment.yield_curve?.spread, 2) }}%</span>
            </div>
            <div class="yield-item">
              <span class="yield-label">2Y</span>
              <span class="yield-num">{{ sentiment.yield_curve?.yield_2y || '--' }}%</span>
            </div>
          </div>
          <div class="indicator-signal" :class="sentiment.yield_curve?.signal">
            {{ isZhLocale ? sentiment.yield_curve?.interpretation : sentiment.yield_curve?.interpretation_en }}
          </div>
        </template>
      </div>

      <!-- 纳斯达克波动率 VXN -->
      <div class="indicator-card">
        <div class="indicator-header">
          <span class="indicator-icon">💻</span>
          <span class="indicator-title">{{ isZhLocale ? '纳斯达克波动率 VXN' : 'NASDAQ Volatility' }}</span>
        </div>
        <template v-if="loadingStates.sentiment">
          <div class="skeleton-indicator">
            <div class="skeleton-line" style="width: 45%; height: 32px;"></div>
          </div>
        </template>
        <template v-else>
          <div class="indicator-value" :class="getVolatilityClass(sentiment.vxn?.level)">
            {{ sentiment.vxn?.value || '--' }}
          </div>
          <div class="indicator-change" :class="(sentiment.vxn?.change || 0) >= 0 ? 'positive' : 'negative'">
            {{ (sentiment.vxn?.change || 0) >= 0 ? '+' : '' }}{{ formatNumber(sentiment.vxn?.change, 2) }}%
          </div>
          <div class="indicator-desc">{{ isZhLocale ? sentiment.vxn?.interpretation : sentiment.vxn?.interpretation_en }}</div>
        </template>
      </div>

      <!-- 黄金波动率 GVZ -->
      <div class="indicator-card">
        <div class="indicator-header">
          <span class="indicator-icon">🥇</span>
          <span class="indicator-title">{{ isZhLocale ? '黄金波动率 GVZ' : 'Gold Volatility' }}</span>
        </div>
        <template v-if="loadingStates.sentiment">
          <div class="skeleton-indicator">
            <div class="skeleton-line" style="width: 45%; height: 32px;"></div>
          </div>
        </template>
        <template v-else>
          <div class="indicator-value" :class="getVolatilityClass(sentiment.gvz?.level)">
            {{ sentiment.gvz?.value || '--' }}
          </div>
          <div class="indicator-change" :class="(sentiment.gvz?.change || 0) >= 0 ? 'positive' : 'negative'">
            {{ (sentiment.gvz?.change || 0) >= 0 ? '+' : '' }}{{ formatNumber(sentiment.gvz?.change, 2) }}%
          </div>
          <div class="indicator-desc">{{ isZhLocale ? sentiment.gvz?.interpretation : sentiment.gvz?.interpretation_en }}</div>
        </template>
      </div>

      <!-- VIX期限结构 -->
      <div class="indicator-card">
        <div class="indicator-header">
          <span class="indicator-icon">📊</span>
          <span class="indicator-title">{{ isZhLocale ? 'VIX期限结构' : 'VIX Term Structure' }}</span>
        </div>
        <template v-if="loadingStates.sentiment">
          <div class="skeleton-indicator">
            <div class="skeleton-line" style="width: 50%; height: 32px;"></div>
          </div>
        </template>
        <template v-else>
          <div class="vix-term-display">
            <div class="term-ratio" :class="getVixTermClass(sentiment.vix_term?.level)">
              {{ sentiment.vix_term?.value || '--' }}
            </div>
            <div class="term-detail">
              <span>VIX: {{ sentiment.vix_term?.vix || '--' }}</span>
              <span>VIX3M: {{ sentiment.vix_term?.vix3m || '--' }}</span>
            </div>
          </div>
          <div class="indicator-signal" :class="sentiment.vix_term?.signal">
            {{ isZhLocale ? sentiment.vix_term?.interpretation : sentiment.vix_term?.interpretation_en }}
          </div>
        </template>
      </div>
    </div>

    <!-- Economic Calendar -->
    <div class="calendar-section">
      <div class="section-header">
        <h2><a-icon type="calendar" /> {{ $t('globalMarket.economicCalendar') }}</h2>
        <a-spin v-if="loadingStates.calendar" size="small" class="section-spinner" />
      </div>

      <!-- 日历骨架屏 -->
      <div v-if="loadingStates.calendar" class="calendar-grid">
        <div v-for="i in 4" :key="'skel-cal-'+i" class="skeleton-calendar-card">
          <div class="skeleton-line" style="width: 40%; height: 16px;"></div>
          <div class="skeleton-line" style="width: 80%; height: 14px; margin-top: 8px;"></div>
          <div class="skeleton-line" style="width: 60%; height: 12px; margin-top: 6px;"></div>
        </div>
      </div>

      <!-- Upcoming Events (Not yet released) -->
      <div
        v-if="!loadingStates.calendar && upcomingEvents.length > 0"
        class="calendar-subsection"
      >
        <h3 class="subsection-title">
          <a-icon type="clock-circle" />
          {{ $t('globalMarket.upcomingEvents') }}
        </h3>
        <div class="calendar-grid">
          <div
            v-for="event in upcomingEvents"
            :key="'upcoming-' + event.id"
            class="calendar-card upcoming"
            :class="event.importance"
          >
            <!-- Impact badge in top-right corner -->
            <div class="card-impact-badge">
              <span
                v-if="event.expected_impact"
                class="impact-tag"
                :class="event.expected_impact"
              >
                <a-icon :type="event.expected_impact === 'bullish' ? 'rise' : event.expected_impact === 'bearish' ? 'fall' : 'minus'" />
                {{ getImpactText(event.expected_impact) }}
              </span>
            </div>
            <div class="card-header">
              <span class="event-country">{{ getCountryFlag(event.country) }}</span>
              <span class="event-name">{{ isZhLocale ? event.name : event.name_en }}</span>
            </div>
            <div class="card-body">
              <div class="event-datetime">
                <a-icon type="calendar" />
                {{ formatEventDate(event.date) }} {{ event.time }}
              </div>
              <div class="event-values">
                <span class="value-item">
                  <span class="label">{{ $t('globalMarket.forecast') }}</span>
                  <span class="value forecast">{{ event.forecast || '--' }}</span>
                </span>
                <span class="value-item">
                  <span class="label">{{ $t('globalMarket.previous') }}</span>
                  <span class="value">{{ event.previous || '--' }}</span>
                </span>
              </div>
            </div>
            <div class="card-footer">
              <span
                class="importance-dot"
                :class="event.importance"
              ></span>
              <span class="importance-text">{{ event.importance }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Released Events -->
      <div
        v-if="!loadingStates.calendar && releasedEvents.length > 0"
        class="calendar-subsection"
      >
        <h3 class="subsection-title">
          <a-icon type="check-circle" />
          {{ $t('globalMarket.releasedEvents') }}
        </h3>
        <div class="calendar-grid">
          <div
            v-for="event in releasedEvents"
            :key="'released-' + event.id"
            class="calendar-card released"
            :class="event.importance"
          >
            <!-- Impact badge in top-right corner -->
            <div class="card-impact-badge">
              <span
                v-if="event.actual_impact"
                class="impact-tag"
                :class="event.actual_impact"
              >
                <a-icon :type="event.actual_impact === 'bullish' ? 'rise' : event.actual_impact === 'bearish' ? 'fall' : 'minus'" />
                {{ getImpactText(event.actual_impact) }}
              </span>
            </div>
            <div class="card-header">
              <span class="event-country">{{ getCountryFlag(event.country) }}</span>
              <span class="event-name">{{ isZhLocale ? event.name : event.name_en }}</span>
            </div>
            <div class="card-body">
              <div class="event-datetime">
                <a-icon type="calendar" />
                {{ formatEventDate(event.date) }} {{ event.time }}
              </div>
              <div class="event-values">
                <span class="value-item actual">
                  <span class="label">{{ $t('globalMarket.actual') }}</span>
                  <span
                    class="value"
                    :class="getActualValueClass(event)"
                  >{{ event.actual || '--' }}</span>
                </span>
                <span class="value-item">
                  <span class="label">{{ $t('globalMarket.forecast') }}</span>
                  <span class="value forecast">{{ event.forecast || '--' }}</span>
                </span>
                <span class="value-item">
                  <span class="label">{{ $t('globalMarket.previous') }}</span>
                  <span class="value">{{ event.previous || '--' }}</span>
                </span>
              </div>
            </div>
            <div class="card-footer">
              <span
                class="importance-dot"
                :class="event.importance"
              ></span>
              <span class="importance-text">{{ event.importance }}</span>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="!loadingStates.calendar && calendar.length === 0"
        class="empty-state"
      >
        <a-icon type="schedule" />
        <span>{{ $t('globalMarket.noEvents') }}</span>
      </div>
    </div>

    <!-- 顶部加载进度条（非全屏遮罩） -->
    <div
      v-if="isAnyLoading"
      class="top-loading-bar"
    >
      <div class="loading-progress"></div>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { mapState } from 'vuex'
import {
  getMarketOverview,
  getMarketHeatmap,
  getEconomicCalendar,
  getMarketSentiment,
  refreshMarketData
} from '@/api/global-market'

export default {
  name: 'GlobalMarket',
  data () {
    return {
      // 各模块独立的 loading 状态
      loadingStates: {
        overview: true,
        heatmap: true,
        calendar: true,
        sentiment: true
      },
      refreshing: false,
      lastUpdateTime: null,
      activeHeatmapTab: 'crypto',
      overview: {
        indices: [],
        forex: [],
        crypto: [],
        commodities: []
      },
      heatmap: {
        crypto: [],
        sectors: [],
        forex: [],
        indices: []
      },
      calendar: [],
      sentiment: {
        fear_greed: null,
        vix: null
      },
      refreshTimer: null,
      worldMapChart: null
    }
  },
  computed: {
    ...mapState({
      navTheme: state => state.app.theme,
      lang: state => state.app.lang
    }),
    isDarkTheme () {
      return this.navTheme === 'dark' || this.navTheme === 'realdark'
    },
    isZhLocale () {
      return this.lang === 'zh-CN' || this.$i18n.locale === 'zh-CN'
    },
    // 计算是否有任何模块还在加载
    isAnyLoading () {
      return Object.values(this.loadingStates).some(v => v)
    },
    upcomingEvents () {
      const now = new Date()
      return this.calendar.filter(event => {
        const eventDate = new Date(`${event.date}T${event.time || '00:00'}`)
        return eventDate > now || !event.actual
      }).slice(0, 8)
    },
    releasedEvents () {
      // 最新发布的排在最前（按 date + time 倒序）
      return this.calendar
        .filter(event => event.actual !== undefined && event.actual !== null && event.actual !== '')
        .sort((a, b) => {
          const ta = new Date(`${a.date}T${a.time || '00:00'}`).getTime()
          const tb = new Date(`${b.date}T${b.time || '00:00'}`).getTime()
          return tb - ta
        })
        .slice(0, 8)
    }
  },
  watch: {
    isDarkTheme () {
      this.$nextTick(() => {
        this.initWorldMap()
      })
    }
  },
  mounted () {
    this.fetchAllData()

    // 价格数据每30秒刷新（overview, heatmap）
    this.priceRefreshTimer = setInterval(() => {
      this.fetchOverview()
      this.fetchHeatmap()
    }, 30000)

    // 情绪数据每2分钟刷新（fear_greed, vix）
    this.sentimentRefreshTimer = setInterval(() => {
      this.fetchSentiment()
    }, 120000)

    // 日历数据每10分钟刷新
    this.calendarRefreshTimer = setInterval(() => {
      this.fetchCalendar()
    }, 600000)
  },
  beforeDestroy () {
    if (this.priceRefreshTimer) {
      clearInterval(this.priceRefreshTimer)
    }
    if (this.sentimentRefreshTimer) {
      clearInterval(this.sentimentRefreshTimer)
    }
    if (this.calendarRefreshTimer) {
      clearInterval(this.calendarRefreshTimer)
    }
    if (this.worldMapChart) {
      this.worldMapChart.dispose()
    }
    window.removeEventListener('resize', this.handleMapResize)
  },
  methods: {
    async fetchAllData (silent = false) {
      // 渐进式加载：各模块独立异步加载，不阻塞页面显示
      if (!silent) {
        this.loadingStates = {
          overview: true,
          heatmap: true,
          calendar: true,
          sentiment: true
        }
      }

      // 并行发起所有请求，但不等待全部完成
      // 各模块加载完成后立即显示
      this.fetchOverview()
      this.fetchHeatmap()
      this.fetchCalendar()
      this.fetchSentiment()

      // 仅在所有请求完成后更新时间（使用 Promise.allSettled 不会因单个失败而中断）
      Promise.allSettled([
        this.fetchOverviewPromise,
        this.fetchHeatmapPromise,
        this.fetchCalendarPromise,
        this.fetchSentimentPromise
      ].filter(Boolean)).then(() => {
        this.lastUpdateTime = Date.now()
      })
    },
    async fetchOverview () {
      this.fetchOverviewPromise = (async () => {
        try {
          const res = await getMarketOverview()
          if (res.code === 1 && res.data) {
            // 合并数据，保留非空数组
            this.overview = {
              indices: res.data.indices || this.overview.indices,
              forex: res.data.forex || this.overview.forex,
              crypto: res.data.crypto || this.overview.crypto,
              commodities: res.data.commodities || this.overview.commodities
            }
            console.log('Market overview loaded:', {
              indices: this.overview.indices?.length || 0,
              forex: this.overview.forex?.length || 0,
              crypto: this.overview.crypto?.length || 0,
              commodities: this.overview.commodities?.length || 0
            })
            // Overview 加载完成后立即初始化地图
            this.$nextTick(() => {
              this.initWorldMap()
            })
          }
        } catch (e) {
          console.error('fetchOverview error:', e)
        } finally {
          this.loadingStates.overview = false
        }
      })()
      return this.fetchOverviewPromise
    },
    async fetchHeatmap () {
      this.fetchHeatmapPromise = (async () => {
        try {
          const res = await getMarketHeatmap()
          if (res.code === 1) {
            this.heatmap = res.data || this.heatmap
          }
        } catch (e) {
          console.error('fetchHeatmap error:', e)
        } finally {
          this.loadingStates.heatmap = false
        }
      })()
      return this.fetchHeatmapPromise
    },
    async fetchCalendar () {
      this.fetchCalendarPromise = (async () => {
        try {
          const res = await getEconomicCalendar()
          if (res.code === 1) {
            this.calendar = res.data || []
          }
        } catch (e) {
          console.error('fetchCalendar error:', e)
        } finally {
          this.loadingStates.calendar = false
        }
      })()
      return this.fetchCalendarPromise
    },
    async fetchSentiment () {
      this.fetchSentimentPromise = (async () => {
        try {
          const res = await getMarketSentiment()
          if (res.code === 1) {
            this.sentiment = res.data || this.sentiment
          }
        } catch (e) {
          console.error('fetchSentiment error:', e)
        } finally {
          this.loadingStates.sentiment = false
        }
      })()
      return this.fetchSentimentPromise
    },
    async handleRefresh () {
      this.refreshing = true
      try {
        await refreshMarketData()
        await this.fetchAllData()
        this.$message.success(this.$t('globalMarket.refreshSuccess'))
      } catch (e) {
        this.$message.error(this.$t('globalMarket.refreshError'))
      } finally {
        this.refreshing = false
      }
    },
    async initWorldMap () {
      const chartDom = this.$refs.worldMap
      if (!chartDom) return

      // 确保容器有正确的尺寸
      const containerWidth = chartDom.offsetWidth
      const containerHeight = chartDom.offsetHeight
      if (containerWidth < 200 || containerHeight < 200) {
        // 容器尺寸不正确，延迟重试
        setTimeout(() => this.initWorldMap(), 100)
        return
      }

      if (this.worldMapChart) {
        this.worldMapChart.dispose()
      }
      this.worldMapChart = echarts.init(chartDom, null, {
        renderer: 'canvas',
        width: containerWidth,
        height: containerHeight
      })

      // Load world map if not already registered
      if (!echarts.getMap('world')) {
        try {
          const response = await fetch('/maps/world.json')
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`)
          }
          const worldJson = await response.json()
          echarts.registerMap('world', worldJson)
          console.log('World map loaded from local file')
        } catch (e) {
          console.error('Failed to load world map:', e)
          this.initFallbackChart()
          return
        }
      }

      const isDark = this.isDarkTheme
      const indices = this.overview.indices || []
      const isZh = this.isZhLocale

      // Prepare scatter data for indices with coordinates
      const scatterData = indices
        .filter(idx => idx.lat && idx.lng)
        .map(idx => ({
          name: isZh ? idx.name_cn : idx.name_en,
          value: [idx.lng, idx.lat, idx.change],
          symbolName: idx.symbol,
          price: idx.price,
          change: idx.change,
          flag: idx.flag,
          region: idx.region
        }))

      const option = {
        backgroundColor: 'transparent',
        animation: true,
        animationDuration: 800,
        animationEasing: 'cubicOut',
        tooltip: {
          trigger: 'item',
          confine: true,
          backgroundColor: isDark ? 'rgba(15, 23, 42, 0.96)' : 'rgba(255, 255, 255, 0.96)',
          borderColor: isDark ? '#334155' : '#e2e8f0',
          borderWidth: 1,
          borderRadius: 8,
          padding: [12, 16],
          textStyle: {
            color: isDark ? '#f1f5f9' : '#1e293b',
            fontSize: 13
          },
          extraCssText: 'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);',
          formatter: (params) => {
            const d = params.data
            if (!d) return ''
            const changeColor = d.change >= 0 ? '#10b981' : '#ef4444'
            const changeSign = d.change >= 0 ? '+' : ''
            const arrow = d.change >= 0 ? '▲' : '▼'
            return `
              <div style="min-width: 140px;">
                <div style="font-size:15px;font-weight:600;margin-bottom:10px;display:flex;align-items:center;gap:6px;">
                  <span style="font-size:18px;">${d.flag}</span>
                  <span>${d.name}</span>
                </div>
                <div style="font-size:22px;font-weight:700;margin-bottom:6px;letter-spacing:-0.5px;">
                  ${this.formatIndexPrice(d.price)}
                </div>
                <div style="color:${changeColor};font-weight:600;font-size:14px;display:flex;align-items:center;gap:4px;">
                  <span>${arrow}</span>
                  <span>${changeSign}${this.formatNumber(d.change, 2)}%</span>
                </div>
              </div>
            `
          }
        },
        geo: {
          map: 'world',
          roam: true,
          zoom: 1.3,
          center: [15, 20],
          scaleLimit: {
            min: 1,
            max: 8
          },
          itemStyle: {
            areaColor: isDark ? '#1e293b' : '#f1f5f9',
            borderColor: isDark ? '#475569' : '#cbd5e1',
            borderWidth: 0.5
          },
          emphasis: {
            disabled: true
          },
          select: {
            disabled: true
          },
          silent: true,
          regions: [
            { name: 'United States', itemStyle: { areaColor: isDark ? '#334155' : '#e2e8f0' } },
            { name: 'China', itemStyle: { areaColor: isDark ? '#334155' : '#e2e8f0' } },
            { name: 'Japan', itemStyle: { areaColor: isDark ? '#334155' : '#e2e8f0' } },
            { name: 'Germany', itemStyle: { areaColor: isDark ? '#334155' : '#e2e8f0' } },
            { name: 'United Kingdom', itemStyle: { areaColor: isDark ? '#334155' : '#e2e8f0' } },
            { name: 'France', itemStyle: { areaColor: isDark ? '#334155' : '#e2e8f0' } },
            { name: 'South Korea', itemStyle: { areaColor: isDark ? '#334155' : '#e2e8f0' } },
            { name: 'Australia', itemStyle: { areaColor: isDark ? '#334155' : '#e2e8f0' } },
            { name: 'India', itemStyle: { areaColor: isDark ? '#334155' : '#e2e8f0' } }
          ]
        },
        series: [
          {
            name: 'Markets',
            type: 'scatter',
            coordinateSystem: 'geo',
            data: scatterData,
            symbol: 'circle',
            symbolSize: 12,
            itemStyle: {
              color: (params) => {
                const change = params.data.change
                return change >= 0 ? '#22c55e' : '#ef4444'
              },
              borderColor: '#fff',
              borderWidth: 2,
              shadowBlur: 6,
              shadowColor: 'rgba(0, 0, 0, 0.3)'
            },
            emphasis: {
              scale: 1.8,
              itemStyle: {
                shadowBlur: 12,
                shadowColor: 'rgba(0, 0, 0, 0.4)'
              },
              label: {
                show: true
              }
            },
            label: {
              show: true,
              position: 'right',
              distance: 8,
              formatter: (params) => {
                const d = params.data
                return `{flag|${d.flag}} {price|${this.formatIndexPrice(d.price)}}`
              },
              rich: {
                flag: {
                  fontSize: 13,
                  verticalAlign: 'middle'
                },
                price: {
                  fontSize: 11,
                  fontWeight: '600',
                  fontFamily: 'SF Mono, Monaco, Consolas, monospace',
                  color: isDark ? '#f1f5f9' : '#1e293b',
                  padding: [2, 6],
                  backgroundColor: isDark ? 'rgba(30, 41, 59, 0.9)' : 'rgba(255, 255, 255, 0.95)',
                  borderRadius: 4,
                  verticalAlign: 'middle'
                }
              }
            },
            labelLayout: {
              hideOverlap: true
            },
            zlevel: 2
          }
        ]
      }

      this.worldMapChart.setOption(option)

      // 确保图表正确渲染
      this.$nextTick(() => {
        if (this.worldMapChart) {
          this.worldMapChart.resize()
        }
      })

      window.addEventListener('resize', this.handleMapResize)
    },
    handleMapResize () {
      if (this.worldMapChart) {
        this.worldMapChart.resize()
      }
    },
    initFallbackChart () {
      // Fallback: show a bar chart when world map fails to load
      const chartDom = this.$refs.worldMap
      if (!chartDom || !this.worldMapChart) return

      const isDark = this.isDarkTheme
      const indices = this.overview.indices || []
      const isZh = this.isZhLocale

      const data = indices.map(idx => ({
        name: (isZh ? idx.name_cn : idx.name_en) || idx.symbol,
        value: idx.change || 0,
        flag: idx.flag,
        price: idx.price
      }))

      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          backgroundColor: isDark ? 'rgba(17, 24, 39, 0.95)' : 'rgba(255, 255, 255, 0.95)',
          borderColor: isDark ? '#374151' : '#e5e7eb',
          textStyle: { color: isDark ? '#f3f4f6' : '#1f2937' },
          formatter: (params) => {
            const d = params[0]
            if (!d) return ''
            const item = data[d.dataIndex]
            const changeColor = item.value >= 0 ? '#10b981' : '#ef4444'
            const sign = item.value >= 0 ? '+' : ''
            return `
              <div style="padding:8px;">
                <div style="font-size:14px;font-weight:600;margin-bottom:4px;">${item.flag} ${item.name}</div>
                <div style="font-size:16px;font-weight:700;margin-bottom:4px;">${this.formatNumber(item.price, 2)}</div>
                <div style="color:${changeColor};font-weight:600;">${sign}${item.value.toFixed(2)}%</div>
              </div>
            `
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: data.map(d => d.flag + ' ' + d.name),
          axisLabel: {
            color: isDark ? '#94a3b8' : '#64748b',
            rotate: 45,
            fontSize: 11
          },
          axisLine: { lineStyle: { color: isDark ? '#334155' : '#e2e8f0' } }
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            color: isDark ? '#94a3b8' : '#64748b',
            formatter: '{value}%'
          },
          splitLine: { lineStyle: { color: isDark ? '#334155' : '#e2e8f0' } }
        },
        series: [{
          type: 'bar',
          data: data.map(d => ({
            value: d.value,
            itemStyle: {
              color: d.value >= 0 ? '#10b981' : '#ef4444',
              borderRadius: [4, 4, 0, 0]
            }
          })),
          barWidth: '60%'
        }]
      }

      this.worldMapChart.setOption(option)
    },
    getLocaleName (item) {
      if (this.isZhLocale) {
        return item.name_cn || item.name || item.symbol
      }
      return item.name_en || item.name || item.symbol
    },
    formatNumber (num, digits = 2) {
      if (num === undefined || num === null || isNaN(num)) return '--'
      return Number(num).toLocaleString('en-US', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
      })
    },
    formatCompact (num) {
      if (!num) return '--'
      if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B'
      if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M'
      if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K'
      return num.toFixed(2)
    },
    // 指数价格格式化：显示完整数字，带千分位分隔符
    formatIndexPrice (num) {
      if (!num && num !== 0) return '--'
      // 对于股指，通常显示2位小数，带千分位
      return Number(num).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    },
    formatTime (ts) {
      if (!ts) return '--'
      return new Date(ts).toLocaleTimeString()
    },
    getMonthName (dateStr) {
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      const month = parseInt(dateStr.split('-')[1], 10)
      return months[month - 1] || ''
    },
    getFearGreedClass (value) {
      if (!value) return ''
      if (value <= 25) return 'extreme-fear'
      if (value <= 45) return 'fear'
      if (value <= 55) return 'neutral'
      if (value <= 75) return 'greed'
      return 'extreme-greed'
    },
    getNeedleRotation (value) {
      // Convert value (0-100) to rotation angle (-90 to 90 degrees)
      const v = Math.max(0, Math.min(100, value || 50))
      return -90 + (v / 100) * 180
    },
    getFearGreedLabel (value) {
      if (!value && value !== 0) return '--'
      if (value <= 25) return this.$t('globalMarket.extremeFear')
      if (value <= 45) return this.$t('globalMarket.fear')
      if (value <= 55) return this.$t('globalMarket.neutral')
      if (value <= 75) return this.$t('globalMarket.greed')
      return this.$t('globalMarket.extremeGreed')
    },
    // 美元指数样式类
    getDxyClass (level) {
      const mapping = {
        strong: 'bullish',
        moderate_strong: 'neutral-bullish',
        neutral: 'neutral',
        moderate_weak: 'neutral-bearish',
        weak: 'bearish'
      }
      return mapping[level] || 'neutral'
    },
    // 收益率曲线样式类
    getYieldCurveClass (level) {
      const mapping = {
        deeply_inverted: 'danger',
        inverted: 'warning',
        flat: 'caution',
        normal: 'good',
        steep: 'excellent'
      }
      return mapping[level] || 'neutral'
    },
    // 波动率指标样式类 (VXN, GVZ)
    getVolatilityClass (level) {
      const mapping = {
        very_low: 'very-low',
        low: 'low',
        moderate: 'moderate',
        high: 'high',
        very_high: 'very-high'
      }
      return mapping[level] || 'moderate'
    },
    // VIX期限结构样式类
    getVixTermClass (level) {
      const mapping = {
        high_fear: 'fear',
        elevated: 'caution',
        normal: 'neutral',
        complacent: 'greed',
        extreme_complacency: 'extreme-greed'
      }
      return mapping[level] || 'neutral'
    },
    getHeatmapClass (value) {
      if (value === null || value === undefined) return 'neutral'
      // More granular classes for gradient effect
      if (value >= 5) return 'very-strong-up'
      if (value >= 3) return 'strong-up'
      if (value >= 1) return 'up'
      if (value >= 0) return 'slight-up'
      if (value <= -5) return 'very-strong-down'
      if (value <= -3) return 'strong-down'
      if (value <= -1) return 'down'
      if (value < 0) return 'slight-down'
      return 'neutral'
    },
    getHeatmapStyle (value) {
      // Dynamic gradient background based on value
      const isDark = this.isDarkTheme

      if (value === null || value === undefined) {
        return {
          background: isDark ? 'rgba(51, 65, 85, 0.4)' : 'rgba(148, 163, 184, 0.2)',
          color: isDark ? '#f1f5f9' : '#64748b'
        }
      }
      if (value >= 0) {
        // Green gradient: more positive = darker green
        const intensity = Math.min(value / 5, 1)
        const r = Math.round(34 + (0 - 34) * intensity)
        const g = Math.round(197 + (128 - 197) * intensity * 0.3)
        const b = Math.round(94 + (0 - 94) * intensity)
        const alpha = isDark ? (0.4 + intensity * 0.5) : (0.3 + intensity * 0.6)
        // 暗色主题下，低亮度使用浅色文字；亮色主题下，低亮度使用深绿色
        const textColor = intensity > 0.5 ? '#fff' : (isDark ? '#34d399' : '#166534')
        return {
          background: `rgba(${r}, ${g}, ${b}, ${alpha})`,
          color: textColor
        }
      } else {
        // Red gradient: more negative = darker red
        const intensity = Math.min(Math.abs(value) / 5, 1)
        const r = Math.round(239 + (180 - 239) * intensity * 0.2)
        const g = Math.round(68 + (0 - 68) * intensity)
        const b = Math.round(68 + (0 - 68) * intensity)
        const alpha = isDark ? (0.4 + intensity * 0.5) : (0.3 + intensity * 0.6)
        // 暗色主题下，低亮度使用浅色文字；亮色主题下，低亮度使用深红色
        const textColor = intensity > 0.5 ? '#fff' : (isDark ? '#f87171' : '#991b1b')
        return {
          background: `rgba(${r}, ${g}, ${b}, ${alpha})`,
          color: textColor
        }
      }
    },
    formatEventDate (dateStr) {
      if (!dateStr) return '--'
      const [, month, day] = dateStr.split('-')
      return `${month}/${day}`
    },
    getActualValueClass (event) {
      if (!event.actual || !event.forecast) return ''
      const actual = parseFloat(event.actual)
      const forecast = parseFloat(event.forecast)
      if (isNaN(actual) || isNaN(forecast)) return ''
      if (event.impact_if_above === 'bullish') {
        return actual > forecast ? 'bullish' : actual < forecast ? 'bearish' : ''
      } else if (event.impact_if_above === 'bearish') {
        return actual > forecast ? 'bearish' : actual < forecast ? 'bullish' : ''
      }
      return ''
    },
    getHeatmapSize (marketCap, type) {
      if (type === 'crypto' && marketCap) {
        const maxCap = Math.max(...(this.heatmap.crypto || []).map(c => c.marketCap || 0))
        const ratio = Math.sqrt(marketCap / maxCap)
        const minSize = 70
        const maxSize = 140
        return Math.max(minSize, Math.min(maxSize, minSize + (maxSize - minSize) * ratio)) + 'px'
      }
      return '100px'
    },
    getImpactText (impact) {
      const texts = {
        'bullish': this.$t('globalMarket.bullish'),
        'bearish': this.$t('globalMarket.bearish'),
        'neutral': this.$t('globalMarket.neutral')
      }
      return texts[impact] || impact
    },
    getCountryFlag (country) {
      const flags = {
        'US': '🇺🇸',
        'CN': '🇨🇳',
        'EU': '🇪🇺',
        'JP': '🇯🇵',
        'UK': '🇬🇧',
        'DE': '🇩🇪',
        'FR': '🇫🇷',
        'INTL': '🌐'
      }
      return flags[country] || '🌐'
    }
  }
}
</script>

<style lang="less" scoped>
// Design tokens
@bg-dark: #0f172a;
@bg-card-dark: #1e293b;
@border-dark: #334155;
@text-primary-dark: #f1f5f9;
@text-secondary-dark: #94a3b8;

@bg-light: #f8fafc;
@bg-card-light: #ffffff;
@border-light: #e2e8f0;
@text-primary-light: #1e293b;
@text-secondary-light: #64748b;

@green: #10b981;
@green-light: #34d399;
@red: #ef4444;
@red-light: #f87171;
@blue: #3b82f6;
@purple: #8b5cf6;
@amber: #f59e0b;
@cyan: #06b6d4;

.global-market {
  min-height: 100vh;
  padding: 20px;
  background: @bg-light;
  transition: background 0.3s;

  &.theme-dark {
    background: @bg-dark;
    color: @text-primary-dark;

    // ==================== 全局文字颜色覆盖 ====================
    .page-title, .section-header h2 { color: @text-primary-dark; }
    .update-time { color: @text-secondary-dark; }

    // ==================== 卡片/区块背景 ====================
    .sentiment-card, .map-section, .heatmap-section, .calendar-section {
      background: @bg-card-dark;
      border-color: @border-dark;
    }

    .sentiment-title { color: @text-primary-dark; }

    // ==================== 日历卡片 ====================
    .calendar-card {
      background: rgba(51, 65, 85, 0.4);
      border-color: @border-dark;

      .card-header .event-name { color: @text-primary-dark; }
      .card-body {
        .event-datetime { color: @text-secondary-dark; }
        .event-values {
          .value-item {
            .label { color: @text-secondary-dark; }
            .value { color: @text-primary-dark; }
            .value.forecast { color: @cyan; }
          }
        }
      }
      .card-footer {
        border-color: @border-dark;
        .importance-text { color: @text-secondary-dark; }
      }

      .card-impact-badge .impact-tag.neutral {
        color: @text-secondary-dark;
      }
    }

    .subsection-title {
      color: @text-secondary-dark !important;
      border-color: @border-dark !important;
    }

    // ==================== 热力图 ====================
    .heatmap-item {
      border-color: rgba(255, 255, 255, 0.1);
      // 低亮度时使用浅色文字
      .heatmap-symbol { color: @text-primary-dark; }
      .heatmap-value { color: @text-primary-dark; }
      .heatmap-price { color: @text-secondary-dark; }
      .sector-stocks { color: @text-secondary-dark; }
    }

    .heatmap-tabs {
      /deep/ .ant-tabs-bar {
        border-color: @border-dark;
      }
      /deep/ .ant-tabs-tab {
        color: @text-secondary-dark;
        &.ant-tabs-tab-active { color: @text-primary-dark; }
      }
      /deep/ .ant-tabs-ink-bar {
        background-color: @blue;
      }
    }

    // ==================== 情绪指标 ====================
    .gauge-container {
      .gauge-label { color: @text-secondary-dark; }
    }
    .gauge-legend {
      color: @text-secondary-dark;
      .legend-item { opacity: 0.9; }
    }

    .vix-display {
      .vix-interpretation { color: @text-secondary-dark; }
      .vix-change {
        &.positive { color: @green-light; }
        &.negative { color: @red-light; }
      }
    }

    // ==================== 状态提示 ====================
    .empty-state, .empty-hint { color: @text-secondary-dark; }

    // ==================== Ant Design 组件覆盖 ====================
    /deep/ .ant-btn {
      &.ant-btn-primary {
        background: @blue;
        border-color: @blue;
      }
    }

    /deep/ .ant-spin-dot-item {
      background-color: @blue;
    }

    /deep/ .ant-tooltip-inner {
      background: @bg-card-dark;
      color: @text-primary-dark;
    }
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .header-left {
      display: flex;
      align-items: baseline;
      gap: 16px;
    }

    .page-title {
      font-size: 24px;
      font-weight: 700;
      color: @text-primary-light;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 10px;
      .anticon { color: @blue; }
    }

    .update-time {
      font-size: 12px;
      color: @text-secondary-light;
    }
  }

  .section-header {
    margin-bottom: 16px;

    h2 {
      font-size: 18px;
      font-weight: 600;
      color: @text-primary-light;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      .anticon { color: @blue; }
    }
  }

  // Map + Heatmap Row Layout
  .map-heatmap-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 24px;

    @media (max-width: 1200px) {
      grid-template-columns: 1fr;
    }
  }

  .map-section {
    background: @bg-card-light;
    border: 1px solid @border-light;
    border-radius: 16px;
    padding: 20px;
    min-height: 420px;
    overflow: hidden;

    .map-wrapper {
      position: relative;
      width: 100%;
      height: 380px;
    }

    .world-map-container {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      transition: opacity 0.3s ease;

      &.map-loading {
        opacity: 0;
      }
    }

    .skeleton-map-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: @bg-light;
      border-radius: 8px;
      overflow: hidden;
      z-index: 10;
    }

    @media (max-width: 768px) {
      min-height: 350px;
      padding: 16px;

      .map-wrapper {
        height: 300px;
      }
    }
  }

  .heatmap-section {
    background: @bg-card-light;
    border: 1px solid @border-light;
    border-radius: 16px;
    padding: 20px;
    min-height: 420px;
    overflow: hidden;
    display: flex;
    flex-direction: column;

    .heatmap-tabs {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      min-height: 0; // allow flex children to size correctly

      /deep/ .ant-tabs-content {
        flex: 1;
        overflow: hidden;
      }

      /deep/ .ant-tabs-tabpane {
        overflow: hidden;
      }

      // 避免 animated 模式产生的横向滚动条（即使未来打开 animated 也不抖）
      /deep/ .ant-tabs-content-animated {
        overflow-x: hidden;
      }
    }

    @media (max-width: 768px) {
      min-height: 350px;
      padding: 16px;
    }
  }

  &.theme-dark {
    .map-section {
      background: @bg-card-dark;
      border-color: @border-dark;

      .skeleton-map-overlay {
        background: @bg-dark;
      }
    }

    .heatmap-section {
      background: @bg-card-dark;
      border-color: @border-dark;
    }
  }

  // Calendar Section
  .calendar-section {
    background: @bg-card-light;
    border: 1px solid @border-light;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 24px;
  }

  .calendar-subsection {
    margin-bottom: 24px;

    &:last-child {
      margin-bottom: 0;
    }

    .subsection-title {
      font-size: 14px;
      font-weight: 600;
      color: @text-secondary-light;
      margin: 0 0 12px 0;
      display: flex;
      align-items: center;
      gap: 6px;
      padding-bottom: 8px;
      border-bottom: 1px dashed @border-light;

      .anticon { font-size: 14px; }

      .theme-dark & {
        color: @text-secondary-dark;
        border-color: @border-dark;
      }
    }
  }

  .calendar-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }

  .calendar-card {
    background: @bg-light;
    border-radius: 12px;
    padding: 14px;
    position: relative;
    transition: all 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    .theme-dark & {
      background: rgba(51, 65, 85, 0.4);

      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      }
    }

    &.high { border-left: 4px solid @red; }
    &.medium { border-left: 4px solid @amber; }
    &.low { border-left: 4px solid @green; }

    &.upcoming {
      border-top: 2px solid @blue;
    }

    .card-impact-badge {
      position: absolute;
      top: 10px;
      right: 10px;

      .impact-tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 12px;

        &.bullish {
          background: rgba(34, 197, 94, 0.15);
          color: @green;
        }

        &.bearish {
          background: rgba(239, 68, 68, 0.15);
          color: @red;
        }

        &.neutral {
          background: rgba(148, 163, 184, 0.15);
          color: @text-secondary-light;

          .theme-dark & {
            color: @text-secondary-dark;
          }
        }
      }
    }

    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
      padding-right: 80px; // Space for impact badge

      .event-country {
        font-size: 16px;
      }

      .event-name {
        font-size: 13px;
        font-weight: 600;
        color: @text-primary-light;
        line-height: 1.3;

        .theme-dark & {
          color: @text-primary-dark;
        }
      }
    }

    .card-body {
      .event-datetime {
        font-size: 12px;
        color: @text-secondary-light;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 4px;

        .anticon { font-size: 11px; }

        .theme-dark & {
          color: @text-secondary-dark;
        }
      }

      .event-values {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;

        .value-item {
          display: flex;
          flex-direction: column;
          gap: 2px;

          &.actual {
            .value {
              font-size: 16px;

              &.bullish { color: @green; }
              &.bearish { color: @red; }
            }
          }

          .label {
            font-size: 10px;
            color: @text-secondary-light;
            text-transform: uppercase;

            .theme-dark & {
              color: @text-secondary-dark;
            }
          }

          .value {
            font-size: 14px;
            font-weight: 600;
            color: @text-primary-light;

            &.forecast { color: @blue; }

            .theme-dark & {
              color: @text-primary-dark;

              &.forecast { color: @cyan; }
            }
          }
        }
      }
    }

    .card-footer {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid @border-light;

      .importance-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;

        &.high { background: @red; }
        &.medium { background: @amber; }
        &.low { background: @green; }
      }

      .importance-text {
        font-size: 10px;
        color: @text-secondary-light;
        text-transform: uppercase;

        .theme-dark & {
          color: @text-secondary-dark;
        }
      }

      .theme-dark & {
        border-color: @border-dark;
      }
    }
  }

  // Sentiment Row
  .sentiment-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 24px;

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }
  }

  .sentiment-card {
    background: @bg-card-light;
    border: 1px solid @border-light;
    border-radius: 16px;
    padding: 20px;

    .sentiment-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;

      .sentiment-title {
        font-size: 16px;
        font-weight: 600;
        color: @text-primary-light;
      }

      .anticon { color: @text-secondary-light; cursor: help; }
    }
  }

  // 暗色主题下的 sentiment-card 特殊样式
  &.theme-dark .sentiment-card {
    .sentiment-header {
      .sentiment-title { color: @text-primary-dark; }
      .anticon { color: @text-secondary-dark; }
    }
  }

  .gauge-container {
    text-align: center;
  }

  .gauge-meter {
    position: relative;
    width: 200px;
    height: 120px;
    margin: 0 auto 16px;

    .gauge-svg {
      width: 100%;
      height: auto;
    }

    .gauge-center {
      position: absolute;
      bottom: 10px;
      left: 50%;
      transform: translateX(-50%);
      text-align: center;

      .gauge-value {
        display: block;
        font-size: 32px;
        font-weight: 700;
        line-height: 1;

        &.extreme-fear { color: #dc2626; }
        &.fear { color: #f87171; }
        &.neutral { color: #fbbf24; }
        &.greed { color: #84cc16; }
        &.extreme-greed { color: #22c55e; }
      }

      .gauge-label {
        font-size: 12px;
        color: @text-secondary-light;
        margin-top: 4px;

        .theme-dark & {
          color: @text-secondary-dark;
        }
      }
    }
  }

  .gauge-legend {
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: @text-secondary-light;

    .theme-dark & {
      color: @text-secondary-dark;
    }

    .legend-item {
      &.extreme-fear { color: #dc2626; }
      &.fear { color: #f87171; }
      &.neutral { color: #fbbf24; }
      &.greed { color: #84cc16; }
      &.extreme-greed { color: #22c55e; }
    }
  }

  .vix-display {
    text-align: center;
    padding: 20px 0;

    .vix-value {
      font-size: 48px;
      font-weight: 700;
      margin-bottom: 8px;

      &.very_low { color: @green; }
      &.low { color: #84cc16; }
      &.moderate { color: @amber; }
      &.high { color: #f97316; }
      &.very_high { color: @red; }
    }

    .vix-change {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 8px;
    }

    .vix-interpretation {
      font-size: 14px;
      color: @text-secondary-light;

      .theme-dark & {
        color: @text-secondary-dark;
      }
    }
  }

  // Additional Indicators Row
  .indicators-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    margin-bottom: 24px;

    @media (max-width: 1200px) {
      grid-template-columns: repeat(3, 1fr);
    }

    @media (max-width: 768px) {
      grid-template-columns: repeat(2, 1fr);
    }

    @media (max-width: 480px) {
      grid-template-columns: 1fr;
    }
  }

  .indicator-card {
    background: @bg-card-light;
    border: 1px solid @border-light;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .indicator-header {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-bottom: 12px;

      .indicator-icon {
        font-size: 20px;
      }

      .indicator-title {
        font-size: 13px;
        font-weight: 600;
        color: @text-primary-light;
      }
    }

    .indicator-value {
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 4px;

      &.bullish { color: #22c55e; }
      &.neutral-bullish { color: #84cc16; }
      &.neutral { color: #94a3b8; }
      &.neutral-bearish { color: #f97316; }
      &.bearish { color: #ef4444; }

      // Volatility levels
      &.very-low { color: #22c55e; }
      &.low { color: #84cc16; }
      &.moderate { color: #eab308; }
      &.high { color: #f97316; }
      &.very-high { color: #ef4444; }
    }

    .indicator-change {
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 8px;
    }

    .indicator-desc {
      font-size: 11px;
      color: @text-secondary-light;
      line-height: 1.4;
    }

    .indicator-signal {
      font-size: 11px;
      padding: 4px 8px;
      border-radius: 4px;
      margin-top: 8px;

      &.bullish {
        background: rgba(34, 197, 94, 0.15);
        color: #22c55e;
      }
      &.bearish {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
      }
      &.neutral {
        background: rgba(148, 163, 184, 0.15);
        color: #64748b;
      }
    }

    // Yield curve specific
    &.yield-curve {
      .yield-values {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin-bottom: 8px;

        .yield-item {
          text-align: center;

          .yield-label {
            font-size: 11px;
            color: @text-secondary-light;
            display: block;
          }

          .yield-num {
            font-size: 18px;
            font-weight: 600;
            color: @text-primary-light;
          }
        }

        .yield-spread {
          text-align: center;
          padding: 6px 10px;
          border-radius: 8px;

          .spread-label {
            font-size: 10px;
            display: block;
            opacity: 0.8;
          }

          .spread-value {
            font-size: 16px;
            font-weight: 700;
          }

          &.danger {
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
          }
          &.warning {
            background: rgba(249, 115, 22, 0.15);
            color: #f97316;
          }
          &.caution {
            background: rgba(234, 179, 8, 0.15);
            color: #eab308;
          }
          &.good {
            background: rgba(132, 204, 22, 0.15);
            color: #84cc16;
          }
          &.excellent {
            background: rgba(34, 197, 94, 0.15);
            color: #22c55e;
          }
        }
      }
    }

    // VIX Term Structure specific
    .vix-term-display {
      .term-ratio {
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 4px;

        &.fear { color: #ef4444; }
        &.caution { color: #f97316; }
        &.neutral { color: #64748b; }
        &.greed { color: #84cc16; }
        &.extreme-greed { color: #22c55e; }
      }

      .term-detail {
        font-size: 11px;
        color: @text-secondary-light;
        display: flex;
        justify-content: center;
        gap: 12px;
      }
    }

    .skeleton-indicator {
      padding: 20px 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }
  }

  // Dark theme for indicators
  &.theme-dark {
    .indicators-row {
      .indicator-card {
        background: @bg-card-dark;
        border-color: @border-dark;

        &:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        }

        .indicator-header .indicator-title {
          color: @text-primary-dark;
        }

        .indicator-desc {
          color: @text-secondary-dark;
        }

        &.yield-curve {
          .yield-values {
            .yield-item {
              .yield-label { color: @text-secondary-dark; }
              .yield-num { color: @text-primary-dark; }
            }
          }
        }

        .vix-term-display .term-detail {
          color: @text-secondary-dark;
        }
      }
    }
  }

  // Heatmap Section
  .heatmap-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 0;
    overflow: hidden;
    max-width: 100%;

    &.sectors-heatmap, &.forex-heatmap {
      .heatmap-item {
        flex-basis: calc(20% - 8px);
        min-width: 100px;
      }
    }
  }

  .heatmap-item {
    border-radius: 10px;
    padding: 12px;
    text-align: center;
    border: 1px solid rgba(0, 0, 0, 0.05);
    transition: all 0.2s;

    &:hover {
      transform: scale(1.05);
      z-index: 1;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .theme-dark & {
      border-color: rgba(255, 255, 255, 0.1);

      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
      }
    }

    .heatmap-symbol {
      font-size: 13px;
      font-weight: 700;
      margin-bottom: 4px;
    }

    .heatmap-value {
      font-size: 12px;
      font-weight: 600;
    }

    .heatmap-price {
      font-size: 10px;
      opacity: 0.8;
      margin-top: 2px;
    }

    .sector-stocks {
      font-size: 9px;
      opacity: 0.6;
      margin-top: 4px;
    }
  }

  // Empty state
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: @text-secondary-light;

    .anticon {
      font-size: 32px;
      margin-bottom: 12px;
      opacity: 0.5;
    }

    .theme-dark & {
      color: @text-secondary-dark;
    }
  }

  // 顶部加载进度条（替代全屏遮罩）
  .top-loading-bar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: rgba(59, 130, 246, 0.2);
    z-index: 9999;
    overflow: hidden;

    .loading-progress {
      height: 100%;
      width: 30%;
      background: linear-gradient(90deg, @blue, @cyan, @blue);
      animation: loading-slide 1.5s ease-in-out infinite;
    }
  }

  @keyframes loading-slide {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
  }

  // Section 内部的小 spinner
  .section-spinner {
    margin-left: 8px;
  }

  .section-header {
    display: flex;
    align-items: center;
  }

  // ==================== 骨架屏样式 ====================

  // 骨架屏基础动画
  @keyframes skeleton-shimmer {
    0% { background-position: -200px 0; }
    100% { background-position: calc(200px + 100%) 0; }
  }

  .skeleton-shimmer {
    background: linear-gradient(90deg,
      rgba(148, 163, 184, 0.1) 25%,
      rgba(148, 163, 184, 0.2) 50%,
      rgba(148, 163, 184, 0.1) 75%);
    background-size: 200px 100%;
    animation: skeleton-shimmer 1.5s ease-in-out infinite;
  }

  .skeleton-line {
    height: 14px;
    border-radius: 4px;
    background: linear-gradient(90deg,
      rgba(148, 163, 184, 0.15) 25%,
      rgba(148, 163, 184, 0.25) 50%,
      rgba(148, 163, 184, 0.15) 75%);
    background-size: 200px 100%;
    animation: skeleton-shimmer 1.5s ease-in-out infinite;
  }

  // 地图骨架屏
  .skeleton-map {
    height: 450px;
    width: 100%;
    border-radius: 12px;
    background: rgba(148, 163, 184, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;

    .skeleton-shimmer {
      width: 100%;
      height: 100%;
    }
  }

  // 侧边面板骨架屏
  .skeleton-panel-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px;
    background: rgba(148, 163, 184, 0.08);
    border-radius: 8px;
    margin-bottom: 8px;

    .skeleton-line {
      height: 12px;
    }
  }

  // 日历骨架屏
  .skeleton-calendar-card {
    background: rgba(148, 163, 184, 0.08);
    border-radius: 12px;
    padding: 16px;
    min-height: 100px;

    .skeleton-line {
      margin-bottom: 0;
    }
  }

  // 情绪指数骨架屏
  .skeleton-sentiment {
    padding: 20px;
    text-align: center;

    .skeleton-gauge {
      width: 160px;
      height: 90px;
      margin: 0 auto 16px;
      border-radius: 80px 80px 0 0;
      background: linear-gradient(90deg,
        rgba(148, 163, 184, 0.1) 25%,
        rgba(148, 163, 184, 0.2) 50%,
        rgba(148, 163, 184, 0.1) 75%);
      background-size: 200px 100%;
      animation: skeleton-shimmer 1.5s ease-in-out infinite;
    }
  }

  // 热力图骨架屏
  .skeleton-heatmap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 0;

    .skeleton-heatmap-item {
      flex-basis: calc(16.66% - 8px);
      min-width: 80px;
      height: 70px;
      border-radius: 10px;
      background: rgba(148, 163, 184, 0.08);
      overflow: hidden;

      .skeleton-shimmer {
        width: 100%;
        height: 100%;
      }
    }
  }

  // 暗色主题下的骨架屏
  &.theme-dark {
    .skeleton-line,
    .skeleton-map,
    .skeleton-panel-item,
    .skeleton-calendar-card,
    .skeleton-sentiment .skeleton-gauge,
    .skeleton-heatmap .skeleton-heatmap-item {
      background: rgba(51, 65, 85, 0.4);
    }

    .skeleton-line,
    .skeleton-shimmer,
    .skeleton-sentiment .skeleton-gauge {
      background: linear-gradient(90deg,
        rgba(51, 65, 85, 0.3) 25%,
        rgba(71, 85, 105, 0.5) 50%,
        rgba(51, 65, 85, 0.3) 75%);
      background-size: 200px 100%;
      animation: skeleton-shimmer 1.5s ease-in-out infinite;
    }

    .top-loading-bar {
      background: rgba(59, 130, 246, 0.1);
    }
  }

  .positive { color: @green; }
  .negative { color: @red; }

  // Tablet breakpoint
  @media (max-width: 1024px) {
    .sentiment-row {
      grid-template-columns: 1fr;
    }

    .calendar-grid {
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    }

    .heatmap-container {
      &.sectors-heatmap, &.forex-heatmap {
        .heatmap-item {
          flex-basis: calc(25% - 8px);
          min-width: 100px;
        }
      }
    }
  }

  // Mobile breakpoint
  @media (max-width: 768px) {
    padding: 12px;

    .page-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;

      .header-left {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }

      .page-title {
        font-size: 20px;
      }
    }

    .map-heatmap-row {
      grid-template-columns: 1fr;
    }

    .map-section {
      min-height: 350px;
      padding: 16px;

      .map-wrapper {
        height: 300px;
      }
    }

    .section-header h2 {
      font-size: 16px;
    }

    .calendar-grid {
      grid-template-columns: 1fr;
    }

    .calendar-card {
      padding: 12px;

      .card-header {
        padding-right: 60px;
      }

      .card-impact-badge .impact-tag {
        font-size: 10px;
        padding: 2px 6px;
      }
    }

    .sentiment-row {
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .sentiment-card {
      padding: 16px;
    }

    .gauge-meter {
      width: 160px;
      height: 100px;
    }

    .gauge-legend {
      font-size: 9px;
      flex-wrap: wrap;
      justify-content: center;
      gap: 4px;
    }

    .vix-display .vix-value {
      font-size: 36px;
    }

    .heatmap-section {
      padding: 16px;
    }

    .heatmap-container {
      gap: 6px;

      .heatmap-item {
        flex-basis: calc(50% - 6px) !important;
        min-width: 80px !important;
        padding: 10px 8px;

        .heatmap-symbol {
          font-size: 11px;
        }

        .heatmap-value {
          font-size: 11px;
        }

        .heatmap-price {
          font-size: 9px;
        }
      }

      &.sectors-heatmap, &.forex-heatmap {
        .heatmap-item {
          flex-basis: calc(50% - 6px) !important;
          min-width: 80px !important;
        }
      }
    }

    .panel-item {
      padding: 8px 10px;
      font-size: 12px;

      .item-price {
        font-size: 12px;
      }

      .item-change {
        font-size: 11px;
      }

      .crypto-icon {
        width: 16px;
        height: 16px;
      }
    }
  }

  // Small mobile
  @media (max-width: 480px) {
    padding: 8px;

    .page-title {
      font-size: 18px;
    }

    .map-section {
      min-height: 280px;
      padding: 12px;

      .map-wrapper {
        height: 240px;
      }
    }

    .calendar-card {
      .card-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 4px;
        padding-right: 50px;
      }

      .event-values {
        flex-direction: column;
        gap: 6px;
      }
    }

    .heatmap-container .heatmap-item {
      flex-basis: calc(50% - 4px) !important;
      padding: 8px 6px;
    }

    .gauge-meter {
      width: 140px;
      height: 90px;
    }

    .gauge-center .gauge-value {
      font-size: 24px;
    }

    .vix-display .vix-value {
      font-size: 32px;
    }
  }
}
</style>
