/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   main.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: gemini <gemini@student.42lausanne.ch>      +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/03/29 00:00:00 by gemini            #+#    #+#             */
/*   Updated: 2026/03/29 00:00:00 by gemini           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include "ft_strlen.h"

static void	run_case(const char *label, const char *value)
{
	printf("%s:%d\n", label, ft_strlen(value));
}

int	main(void)
{
	run_case("empty", "");
	run_case("hello", "hello");
	run_case("campus", "42 Lausanne");
	return (0);
}
