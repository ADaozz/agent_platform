package org.example.backend.statistics.vo.chart;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 柱状图 / 折线图。
 * 前端：xAxis.data = categories；series[i].name/data = series[i]
 */
@Data
public class CategoryChartVO {

    /** xAxis.data */
    private List<String> categories = new ArrayList<>();

    private List<ChartSeriesVO> series = new ArrayList<>();
}
