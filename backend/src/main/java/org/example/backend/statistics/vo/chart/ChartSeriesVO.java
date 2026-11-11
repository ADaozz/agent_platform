package org.example.backend.statistics.vo.chart;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 对应 ECharts series 单项：{ name, type: 'bar'|'line', data }。
 * type 由前端按图表类型指定，后端只返回 name + data。
 */
@Data
public class ChartSeriesVO {

    private String name;

    private List<Long> data = new ArrayList<>();
}
