package org.example.backend.statistics.service.impl;

import org.apache.shiro.SecurityUtils;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.security.context.LoginUserUtils;
import org.example.backend.statistics.constant.DashboardScope;
import org.example.backend.statistics.mapper.CountGroupRow;
import org.example.backend.statistics.mapper.DashboardMapper;
import org.example.backend.statistics.service.DashboardService;
import org.example.backend.statistics.vo.DashboardKpiVO;
import org.example.backend.statistics.vo.DashboardOverviewVO;
import org.example.backend.statistics.vo.chart.CategoryChartVO;
import org.example.backend.statistics.vo.chart.ChartSeriesVO;
import org.example.backend.statistics.vo.chart.PieChartVO;
import org.example.backend.statistics.vo.chart.PieItemVO;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class DashboardServiceImpl implements DashboardService {

    private static final String PERM_VIEW_ALL = "dashboard:view:all";

    @Resource
    private DashboardMapper dashboardMapper;

    @Override
    // 获取仪表盘概览数据
    public DashboardOverviewVO getOverview(String scope) {
        String normalizedScope = normalizeScope(scope);
        Long ownerUserId = resolveOwnerUserId(normalizedScope);

        DashboardOverviewVO overview = new DashboardOverviewVO();
        overview.setKpi(buildKpi(normalizedScope, ownerUserId));
        overview.setVmByLifecycle(toPieChart(dashboardMapper.countVmByLifecycle(ownerUserId)));
        overview.setVmByEnv(toPieChart(dashboardMapper.countVmByEnv(ownerUserId)));
        overview.setVmByNetworkZone(toPieChart(dashboardMapper.countVmByNetworkZone(ownerUserId)));
        overview.setAppByStatus(toPieChart(dashboardMapper.countAppByStatus(ownerUserId)));
        overview.setVmCreateTrend(toCategoryChart(
                "新增虚机",
                dashboardMapper.countVmCreateTrend(ownerUserId)
        ));

        if (DashboardScope.isAll(normalizedScope)) {
            overview.setOwnerRank(toCategoryChart("虚机数", dashboardMapper.countVmByOwner()));
            overview.setPhysicalHostDistribution(toCategoryChart(
                    "虚机数",
                    dashboardMapper.countVmByPhysicalHost()
            ));
        }

        return overview;
    }

    @Override
    // 获取KPI指标数据
    public DashboardKpiVO getKpi(String scope) {
        String normalizedScope = normalizeScope(scope);
        return buildKpi(normalizedScope, resolveOwnerUserId(normalizedScope));
    }

    @Override
    // 按生命周期统计虚机分布
    public PieChartVO getVmByLifecycle(String scope) {
        return toPieChart(dashboardMapper.countVmByLifecycle(resolveOwnerUserId(normalizeScope(scope))));
    }

    @Override
    // 按环境统计虚机分布
    public PieChartVO getVmByEnv(String scope) {
        return toPieChart(dashboardMapper.countVmByEnv(resolveOwnerUserId(normalizeScope(scope))));
    }

    @Override
    // 按网络区域统计虚机分布
    public PieChartVO getVmByNetworkZone(String scope) {
        return toPieChart(dashboardMapper.countVmByNetworkZone(resolveOwnerUserId(normalizeScope(scope))));
    }

    @Override
    // 按状态统计应用分布
    public PieChartVO getAppByStatus(String scope) {
        return toPieChart(dashboardMapper.countAppByStatus(resolveOwnerUserId(normalizeScope(scope))));
    }

    @Override
    // 获取虚机新增趋势图
    public CategoryChartVO getVmCreateTrend(String scope) {
        return toCategoryChart(
                "新增虚机",
                dashboardMapper.countVmCreateTrend(resolveOwnerUserId(normalizeScope(scope)))
        );
    }

    @Override
    // 获取虚机归属排行
    public CategoryChartVO getOwnerRank() {
        assertViewAllPermission();
        return toCategoryChart("虚机数", dashboardMapper.countVmByOwner());
    }

    @Override
    // 获取物理主机虚机分布
    public CategoryChartVO getPhysicalHostDistribution() {
        assertViewAllPermission();
        return toCategoryChart("虚机数", dashboardMapper.countVmByPhysicalHost());
    }

    // 构建KPI指标
    private DashboardKpiVO buildKpi(String scope, Long ownerUserId) {
        DashboardKpiVO kpi = new DashboardKpiVO();
        kpi.setScope(scope);
        kpi.setVmHostCount(nullToZero(dashboardMapper.countVmHost(ownerUserId)));
        kpi.setVmHostRunningCount(nullToZero(dashboardMapper.countVmHostRunning(ownerUserId)));
        kpi.setVmAppCount(nullToZero(dashboardMapper.countVmApp(ownerUserId)));
        kpi.setCpuCoresTotal(nullToZero(dashboardMapper.sumCpuCores(ownerUserId)));
        kpi.setMemoryGbTotal(nullToZero(dashboardMapper.sumMemoryGb(ownerUserId)));
        if (DashboardScope.isAll(scope)) {
            kpi.setUserCount(nullToZero(dashboardMapper.countUsers()));
        }
        return kpi;
    }

    // 规范化并校验统计范围
    private String normalizeScope(String scope) {
        String normalized = scope == null || scope.trim().isEmpty()
                ? DashboardScope.MINE
                : scope.trim().toLowerCase();
        if (!DashboardScope.isMine(normalized) && !DashboardScope.isAll(normalized)) {
            throw new BusinessException(Module.ModuleType.STATISTICS, "scope 仅支持 mine 或 all", null);
        }
        if (DashboardScope.isAll(normalized)) {
            assertViewAllPermission();
        }
        return normalized;
    }

    // 根据范围解析归属用户ID
    private Long resolveOwnerUserId(String scope) {
        if (DashboardScope.isAll(scope)) {
            return null;
        }
        Long userId = LoginUserUtils.getUserId();
        if (userId == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "未登录", null);
        }
        return userId;
    }

    // 校验全局统计查看权限
    private void assertViewAllPermission() {
        if (!SecurityUtils.getSubject().isPermitted(PERM_VIEW_ALL)) {
            throw new BusinessException(Module.ModuleType.STATISTICS, "无权查看全局统计", null);
        }
    }

    // 将分组统计转换为饼图
    private PieChartVO toPieChart(List<CountGroupRow> rows) {
        PieChartVO chart = new PieChartVO();
        if (rows == null || rows.isEmpty()) {
            return chart;
        }
        chart.setData(rows.stream()
                .map(row -> new PieItemVO(row.getName(), nullToZero(row.getValue())))
                .collect(Collectors.toList()));
        return chart;
    }

    // 将分组统计转换为分类图
    private CategoryChartVO toCategoryChart(String seriesName, List<CountGroupRow> rows) {
        CategoryChartVO chart = new CategoryChartVO();
        if (rows == null || rows.isEmpty()) {
            chart.setSeries(Collections.singletonList(newChartSeries(seriesName, Collections.emptyList())));
            return chart;
        }
        chart.setCategories(rows.stream().map(CountGroupRow::getName).collect(Collectors.toList()));
        chart.setSeries(Collections.singletonList(newChartSeries(
                seriesName,
                rows.stream().map(row -> nullToZero(row.getValue())).collect(Collectors.toList())
        )));
        return chart;
    }

    // 创建图表数据系列
    private ChartSeriesVO newChartSeries(String name, List<Long> data) {
        ChartSeriesVO series = new ChartSeriesVO();
        series.setName(name);
        series.setData(data);
        return series;
    }

    // 将null转为0
    private Long nullToZero(Long value) {
        return value == null ? 0L : value;
    }
}
