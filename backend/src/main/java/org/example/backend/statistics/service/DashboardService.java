package org.example.backend.statistics.service;

import org.example.backend.statistics.vo.DashboardKpiVO;
import org.example.backend.statistics.vo.DashboardOverviewVO;
import org.example.backend.statistics.vo.chart.CategoryChartVO;
import org.example.backend.statistics.vo.chart.PieChartVO;

public interface DashboardService {

    DashboardOverviewVO getOverview(String scope);

    DashboardKpiVO getKpi(String scope);

    PieChartVO getVmByLifecycle(String scope);

    PieChartVO getVmByEnv(String scope);

    PieChartVO getVmByNetworkZone(String scope);

    PieChartVO getAppByStatus(String scope);

    CategoryChartVO getVmCreateTrend(String scope);

    CategoryChartVO getOwnerRank();

    CategoryChartVO getPhysicalHostDistribution();
}
